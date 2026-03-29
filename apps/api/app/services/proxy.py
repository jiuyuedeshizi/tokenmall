from datetime import datetime, timezone
from decimal import Decimal
import json
from time import perf_counter
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApiKey, UsageLog, User
from app.services.pricing import calculate_usage_cost, get_model_or_404
from app.services.tokenizer import estimate_chat_messages_tokens
from app.services.wallet import (
    capture_usage_reservation,
    create_usage_reservation,
    get_available_balance,
    get_wallet_account,
    release_usage_reservation,
)

DEFAULT_MAX_OUTPUT_TOKENS = 1024
RESERVE_BUFFER_MULTIPLIER = Decimal("1.10")


def estimate_prompt_tokens(payload: dict) -> int:
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return 1
    return estimate_chat_messages_tokens(messages)


def estimate_reserved_amount(model, payload: dict) -> tuple[int, int, Decimal]:
    estimated_input_tokens = estimate_prompt_tokens(payload)
    estimated_output_tokens = int(payload.get("max_tokens") or DEFAULT_MAX_OUTPUT_TOKENS)
    estimated_amount = calculate_usage_cost(model, estimated_input_tokens, estimated_output_tokens)
    reserved_amount = (estimated_amount * RESERVE_BUFFER_MULTIPLIER).quantize(Decimal("0.0001"))
    return estimated_input_tokens, estimated_output_tokens, reserved_amount


def assert_key_can_call(api_key: ApiKey, user: User, db: Session):
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    if api_key.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key 不可用")

    wallet = get_wallet_account(user.id, db)
    if api_key.status == "arrears" and get_available_balance(wallet) > Decimal("0"):
        api_key.status = "active"
        db.flush()

    if get_available_balance(wallet) <= Decimal("0"):
        api_key.status = "arrears"
        db.commit()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="余额不足")


def assert_usage_limits(api_key: ApiKey, next_tokens: int, next_amount: Decimal):
    if api_key.token_limit and api_key.used_tokens + next_tokens > api_key.token_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出 Token 限额")
    if api_key.request_limit and api_key.used_requests + 1 > api_key.request_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出请求限额")
    if api_key.budget_limit and Decimal(api_key.used_amount) + next_amount > Decimal(api_key.budget_limit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出预算限额")


def _record_proxy_error(
    *,
    user: User,
    api_key: ApiKey,
    request_id: str,
    model_code: str,
    error_message: str,
    response_time_ms: int | None,
    db: Session,
):
    db.add(
        UsageLog(
            user_id=user.id,
            api_key_id=api_key.id,
            model_code=model_code,
            request_id=request_id,
            response_time_ms=response_time_ms,
            status="error",
            error_message=error_message[:255],
        )
    )
    db.commit()


def _finalize_success(
    *,
    api_key: ApiKey,
    user: User,
    model,
    request_id: str,
    upstream_id: str,
    usage: dict,
    response_time_ms: int,
    db: Session,
):
    prompt_tokens = int(usage.get("prompt_tokens", 0))
    completion_tokens = int(usage.get("completion_tokens", 0))
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
    amount = calculate_usage_cost(model, prompt_tokens, completion_tokens)
    api_key.used_tokens += total_tokens
    api_key.used_requests += 1
    api_key.used_amount = Decimal(api_key.used_amount) + amount
    api_key.last_used_at = datetime.now(timezone.utc)

    if api_key.budget_limit and Decimal(api_key.used_amount) >= Decimal(api_key.budget_limit):
        api_key.status = "quota_exceeded"
    elif api_key.token_limit and api_key.used_tokens >= api_key.token_limit:
        api_key.status = "quota_exceeded"
    elif api_key.request_limit and api_key.used_requests >= api_key.request_limit:
        api_key.status = "quota_exceeded"

    capture_usage_reservation(
        request_id=request_id,
        actual_amount=amount,
        description=f"{model.display_name} 调用扣费",
        reference_id=upstream_id,
        db=db,
    )

    db.add(
        UsageLog(
            user_id=user.id,
            api_key_id=api_key.id,
            model_code=model.model_code,
            request_id=upstream_id,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=total_tokens,
            amount=amount,
            response_time_ms=response_time_ms,
            status="success",
            error_message="",
        )
    )
    db.commit()


async def proxy_chat_completion(api_key: ApiKey, user: User, payload: dict, db: Session):
    assert_key_can_call(api_key, user, db)

    model = get_model_or_404(payload.get("model", ""), db)
    upstream_payload = dict(payload)
    upstream_payload["model"] = model.model_code
    estimated_input_tokens, estimated_output_tokens, reserved_amount = estimate_reserved_amount(model, payload)

    if api_key.request_limit and api_key.used_requests + 1 > api_key.request_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出请求限额")
    if api_key.token_limit and api_key.used_tokens + estimated_input_tokens + estimated_output_tokens > api_key.token_limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出 Token 限额")
    if api_key.budget_limit and Decimal(api_key.used_amount) + reserved_amount > Decimal(api_key.budget_limit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="超出预算限额")

    request_id = f"req_{uuid4().hex}"
    stream_enabled = bool(payload.get("stream"))
    if stream_enabled:
        stream_options = upstream_payload.get("stream_options") or {}
        if not isinstance(stream_options, dict):
            stream_options = {}
        stream_options["include_usage"] = True
        upstream_payload["stream_options"] = stream_options

    create_usage_reservation(
        user_id=user.id,
        api_key=api_key,
        model_code=model.model_code,
        request_id=request_id,
        reserved_amount=reserved_amount,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        db=db,
    )

    if stream_enabled:
        return await proxy_chat_completion_stream(
            api_key=api_key,
            user=user,
            payload=payload,
            upstream_payload=upstream_payload,
            model=model,
            request_id=request_id,
            db=db,
        )

    try:
        started_at = perf_counter()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.litellm_url}/v1/chat/completions",
                json=upstream_payload,
                headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
            )
            response.raise_for_status()
        response_time_ms = int((perf_counter() - started_at) * 1000)
    except httpx.HTTPError as exc:
        response_time_ms = int((perf_counter() - started_at) * 1000) if "started_at" in locals() else None
        release_usage_reservation(request_id=request_id, error_message=str(exc), db=db)
        _record_proxy_error(
            user=user,
            api_key=api_key,
            request_id=request_id,
            model_code=payload.get("model", ""),
            error_message=str(exc),
            response_time_ms=response_time_ms,
            db=db,
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="模型服务调用失败") from exc

    data = response.json()
    _finalize_success(
        api_key=api_key,
        user=user,
        model=model,
        request_id=request_id,
        upstream_id=str(data.get("id", request_id)),
        usage=data.get("usage", {}),
        response_time_ms=response_time_ms,
        db=db,
    )
    return data


async def proxy_chat_completion_stream(
    *,
    api_key: ApiKey,
    user: User,
    payload: dict,
    upstream_payload: dict,
    model,
    request_id: str,
    db: Session,
):
    started_at = perf_counter()
    client = httpx.AsyncClient(timeout=None)
    try:
        request = client.build_request(
            "POST",
            f"{settings.litellm_url}/v1/chat/completions",
            json=upstream_payload,
            headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
        )
        upstream_response = await client.send(request, stream=True)
        upstream_response.raise_for_status()
    except httpx.HTTPError as exc:
        response_time_ms = int((perf_counter() - started_at) * 1000)
        release_usage_reservation(request_id=request_id, error_message=str(exc), db=db)
        _record_proxy_error(
            user=user,
            api_key=api_key,
            request_id=request_id,
            model_code=payload.get("model", ""),
            error_message=str(exc),
            response_time_ms=response_time_ms,
            db=db,
        )
        await client.aclose()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="模型服务调用失败") from exc

    async def stream_generator():
        pending = ""
        usage: dict | None = None
        upstream_id = request_id
        response_time_ms: int | None = None
        finalized = False
        stream_error: str | None = None
        try:
            async for chunk in upstream_response.aiter_text():
                pending += chunk
                yield chunk.encode("utf-8")
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    stripped = line.strip()
                    if not stripped.startswith("data:"):
                        continue
                    data_text = stripped[5:].strip()
                    if not data_text or data_text == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        upstream_id = str(event.get("id", upstream_id))
                        if isinstance(event.get("usage"), dict):
                            usage = event["usage"]

            response_time_ms = int((perf_counter() - started_at) * 1000)
            if usage is None:
                stream_error = "流式响应未返回 usage 数据"
                release_usage_reservation(request_id=request_id, error_message=stream_error, db=db)
                _record_proxy_error(
                    user=user,
                    api_key=api_key,
                    request_id=request_id,
                    model_code=model.model_code,
                    error_message=stream_error,
                    response_time_ms=response_time_ms,
                    db=db,
                )
                return

            _finalize_success(
                api_key=api_key,
                user=user,
                model=model,
                request_id=request_id,
                upstream_id=upstream_id,
                usage=usage,
                response_time_ms=response_time_ms,
                db=db,
            )
            finalized = True
        except Exception as exc:  # noqa: BLE001
            stream_error = str(exc)
            response_time_ms = int((perf_counter() - started_at) * 1000)
            if not finalized:
                release_usage_reservation(request_id=request_id, error_message=stream_error, db=db)
                _record_proxy_error(
                    user=user,
                    api_key=api_key,
                    request_id=request_id,
                    model_code=model.model_code,
                    error_message=stream_error,
                    response_time_ms=response_time_ms,
                    db=db,
                )
            raise
        finally:
            await upstream_response.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_generator(),
        media_type=upstream_response.headers.get("content-type", "text/event-stream; charset=utf-8"),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
