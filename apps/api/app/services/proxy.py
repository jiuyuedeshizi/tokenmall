from datetime import datetime, timezone
from decimal import Decimal
import json
from time import perf_counter
from uuid import uuid4

import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.models import ApiKey, UsageLog, User
from app.services.pricing import calculate_usage_cost
from app.services.tokenizer import count_text_tokens, estimate_chat_messages_tokens
from app.services.wallet import (
    capture_usage_reservation,
    create_usage_reservation,
    get_available_balance,
    get_wallet_account,
    release_usage_reservation,
)

DEFAULT_MAX_OUTPUT_TOKENS = 1024
RESERVE_BUFFER_MULTIPLIER = Decimal("1.10")
HOP_BY_HOP_HEADERS = {
    "authorization",
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def estimate_character_count(payload: dict) -> int:
    input_value = payload.get("input")
    if not isinstance(input_value, dict):
        return 0
    text = input_value.get("text")
    if not isinstance(text, str):
        return 0
    return len(text)


def estimate_video_seconds(payload: dict) -> int:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        return 0
    raw_duration = parameters.get("duration")
    try:
        return max(0, int(raw_duration or 0))
    except (TypeError, ValueError):
        return 0


def estimate_video_audio_enabled(payload: dict) -> bool | None:
    parameters = payload.get("parameters")
    if isinstance(parameters, dict) and parameters.get("audio") is False:
        return False

    input_value = payload.get("input")
    if isinstance(input_value, dict) and input_value.get("audio_url"):
        return True

    if isinstance(parameters, dict) and "audio" in parameters:
        return bool(parameters.get("audio"))
    return None


def estimate_video_resolution(payload: dict) -> str | None:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        return None
    resolution = parameters.get("resolution")
    if not isinstance(resolution, str):
        return None
    return resolution.strip().upper() or None


def build_openai_error_response(
    *,
    message: str,
    error_type: str,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type}},
    )


def raise_openai_error(status_code: int, message: str, error_type: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"message": message, "type": error_type}},
    )


def _extract_error_message(detail: object, fallback: str) -> str:
    if isinstance(detail, dict):
        error = detail.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or fallback)
        return str(detail.get("message") or detail.get("detail") or fallback)
    if isinstance(detail, str):
        return detail
    return fallback


def _coerce_error_type(status_code: int) -> str:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "invalid_api_key"
    if status_code == status.HTTP_402_PAYMENT_REQUIRED:
        return "insufficient_balance"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "permission_denied"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found_error"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "rate_limit_exceeded"
    return "invalid_request_error"


def openai_error_from_http_exception(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("error"), dict):
        payload = detail
    else:
        payload = {
            "error": {
                "message": _extract_error_message(detail, "请求处理失败"),
                "type": _coerce_error_type(exc.status_code),
            }
        }
    return JSONResponse(status_code=exc.status_code, content=payload)


def estimate_prompt_tokens(payload: dict) -> int:
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        return 1
    return estimate_chat_messages_tokens(messages)


def estimate_reserved_amount(model, payload: dict) -> tuple[int, int, Decimal]:
    billing_mode = (model.billing_mode or "token").strip().lower()
    if billing_mode == "per_image":
        parameters = payload.get("parameters")
        image_count = 1
        if isinstance(parameters, dict):
            raw_n = parameters.get("n") or 1
            try:
                image_count = max(1, int(raw_n))
            except (TypeError, ValueError):
                image_count = 1
        estimated_amount = calculate_usage_cost(model, 0, 0, image_count=image_count)
        reserved_amount = (estimated_amount * RESERVE_BUFFER_MULTIPLIER).quantize(Decimal("0.0001"))
        return 0, image_count, reserved_amount
    if billing_mode == "per_10k_chars":
        estimated_chars = estimate_character_count(payload)
        estimated_amount = calculate_usage_cost(model, 0, 0, char_count=estimated_chars)
        reserved_amount = (estimated_amount * RESERVE_BUFFER_MULTIPLIER).quantize(Decimal("0.0001"))
        return estimated_chars, 0, reserved_amount
    if billing_mode == "per_second":
        estimated_seconds = estimate_video_seconds(payload)
        estimated_amount = calculate_usage_cost(
            model,
            0,
            0,
            second_count=estimated_seconds,
            resolution=estimate_video_resolution(payload),
            audio=estimate_video_audio_enabled(payload),
        )
        reserved_amount = (estimated_amount * RESERVE_BUFFER_MULTIPLIER).quantize(Decimal("0.0001"))
        return estimated_seconds, 0, reserved_amount
    estimated_input_tokens = estimate_prompt_tokens(payload)
    estimated_output_tokens = int(payload.get("max_tokens") or DEFAULT_MAX_OUTPUT_TOKENS)
    estimated_amount = calculate_usage_cost(model, estimated_input_tokens, estimated_output_tokens)
    reserved_amount = (estimated_amount * RESERVE_BUFFER_MULTIPLIER).quantize(Decimal("0.0001"))
    return estimated_input_tokens, estimated_output_tokens, reserved_amount


def assert_key_can_call(api_key: ApiKey, user: User, db: Session) -> None:
    if user.status != "active":
        raise_openai_error(status.HTTP_403_FORBIDDEN, "用户已被禁用", "permission_denied")

    wallet = get_wallet_account(user.id, db)
    if api_key.status == "arrears" and get_available_balance(wallet) > Decimal("0"):
        api_key.status = "active"
        db.flush()
    if api_key.status != "active":
        raise_openai_error(status.HTTP_403_FORBIDDEN, "API Key 不可用", "permission_denied")

    if get_available_balance(wallet) <= Decimal("0"):
        api_key.status = "arrears"
        db.commit()
        raise_openai_error(status.HTTP_402_PAYMENT_REQUIRED, "余额不足", "insufficient_balance")


def assert_usage_limits(api_key: ApiKey, next_tokens: int, next_amount: Decimal) -> None:
    if api_key.token_limit and api_key.used_tokens + next_tokens > api_key.token_limit:
        raise_openai_error(status.HTTP_403_FORBIDDEN, "超出 Token 限额", "permission_denied")
    if api_key.request_limit and api_key.used_requests + 1 > api_key.request_limit:
        raise_openai_error(status.HTTP_403_FORBIDDEN, "超出请求限额", "permission_denied")
    if api_key.budget_limit and Decimal(api_key.used_amount) + next_amount > Decimal(api_key.budget_limit):
        raise_openai_error(status.HTTP_403_FORBIDDEN, "超出预算限额", "permission_denied")


def _record_proxy_error(
    *,
    user: User,
    api_key: ApiKey,
    request_id: str,
    model_code: str,
    error_message: str,
    response_time_ms: int | None,
    db: Session,
) -> None:
    db.add(
        UsageLog(
            user_id=user.id,
            api_key_id=api_key.id,
            model_code=model_code,
            request_id=request_id,
            response_time_ms=response_time_ms,
            status="error",
            billing_source="error",
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
    billing_source: str,
    db: Session,
) -> None:
    billing_mode = (model.billing_mode or "token").strip().lower()
    if billing_mode == "per_image":
        image_count = int(usage.get("image_count", 1) or 1)
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        amount = calculate_usage_cost(model, 0, 0, image_count=image_count)
    elif billing_mode == "per_10k_chars":
        char_count = int(usage.get("char_count", 0) or 0)
        prompt_tokens = char_count
        completion_tokens = 0
        total_tokens = char_count
        amount = calculate_usage_cost(model, 0, 0, char_count=char_count)
    elif billing_mode == "per_second":
        second_count = int(usage.get("second_count", 0) or 0)
        prompt_tokens = second_count
        completion_tokens = 0
        total_tokens = second_count
        amount = calculate_usage_cost(
            model,
            0,
            0,
            second_count=second_count,
            resolution=str(usage.get("resolution") or "") or None,
            audio=usage.get("audio") if isinstance(usage.get("audio"), bool) else None,
        )
    else:
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
        billing_source=billing_source,
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
            billing_source=billing_source,
            response_time_ms=response_time_ms,
            status="success",
            error_message="",
        )
    )
    db.commit()


def before_request(*, api_key: ApiKey, user: User, payload: dict, model, db: Session) -> str:
    assert_key_can_call(api_key, user, db)
    estimated_input_tokens, estimated_output_tokens, reserved_amount = estimate_reserved_amount(model, payload)
    assert_usage_limits(api_key, estimated_input_tokens + estimated_output_tokens, reserved_amount)

    request_id = f"req_{uuid4().hex}"
    create_usage_reservation(
        user_id=user.id,
        api_key=api_key,
        model_code=model.model_code,
        request_id=request_id,
        reserved_amount=reserved_amount,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        billing_source="reserved_estimate",
        db=db,
    )
    return request_id


def after_response(
    *,
    api_key: ApiKey,
    user: User,
    model,
    request_id: str,
    response_payload: dict,
    response_time_ms: int,
    db: Session,
) -> None:
    usage = response_payload.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("响应未返回 usage 数据")
    _finalize_success(
        api_key=api_key,
        user=user,
        model=model,
        request_id=request_id,
        upstream_id=str(response_payload.get("id", request_id)),
        usage=usage,
        response_time_ms=response_time_ms,
        billing_source="provider_usage",
        db=db,
    )


def after_estimated_stream_response(
    *,
    api_key: ApiKey,
    user: User,
    model,
    request_id: str,
    payload: dict,
    output_text: str,
    upstream_id: str,
    response_time_ms: int,
    db: Session,
) -> None:
    prompt_tokens = estimate_prompt_tokens(payload)
    completion_tokens = count_text_tokens(output_text)
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    _finalize_success(
        api_key=api_key,
        user=user,
        model=model,
        request_id=request_id,
        upstream_id=upstream_id,
        usage=usage,
        response_time_ms=response_time_ms,
        billing_source="estimated_stream",
        db=db,
    )


def after_estimated_character_response(
    *,
    api_key: ApiKey,
    user: User,
    model,
    request_id: str,
    payload: dict,
    upstream_id: str,
    response_time_ms: int,
    db: Session,
) -> None:
    usage = {"char_count": estimate_character_count(payload)}
    _finalize_success(
        api_key=api_key,
        user=user,
        model=model,
        request_id=request_id,
        upstream_id=upstream_id,
        usage=usage,
        response_time_ms=response_time_ms,
        billing_source="estimated_chars",
        db=db,
    )


def on_error(
    *,
    api_key: ApiKey,
    user: User,
    request_id: str,
    model_code: str,
    error_message: str,
    response_time_ms: int | None,
    db: Session,
) -> None:
    release_usage_reservation(request_id=request_id, error_message=error_message, db=db)
    _record_proxy_error(
        user=user,
        api_key=api_key,
        request_id=request_id,
        model_code=model_code,
        error_message=error_message,
        response_time_ms=response_time_ms,
        db=db,
    )


def _build_upstream_headers(request: Request, provider_api_key: str, provider_headers: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    headers["authorization"] = f"Bearer {provider_api_key}"
    for key, value in (provider_headers or {}).items():
        headers[key] = value
    return headers


def _build_downstream_headers(headers: httpx.Headers) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


def _upstream_error_response(response: httpx.Response) -> JSONResponse:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return JSONResponse(status_code=response.status_code, content=payload)
    except ValueError:
        payload = None

    message = response.text.strip() or "模型服务调用失败"
    return build_openai_error_response(
        status_code=response.status_code,
        message=message,
        error_type="upstream_error",
    )


def _extract_text_from_delta_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "".join(parts)
    return ""


async def forward_request(
    request: Request,
    provider_url: str,
    api_key: str,
    provider_headers: dict[str, str] | None = None,
    method: str = "POST",
) -> Response | JSONResponse:
    body = await request.body() if method.upper() != "GET" else None
    headers = _build_upstream_headers(request, api_key, provider_headers)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream_response = await client.request(
                method.upper(),
                provider_url,
                content=body,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": str(exc), "type": "upstream_error"}},
        ) from exc

    if upstream_response.status_code >= 400:
        return _upstream_error_response(upstream_response)

    downstream_headers = _build_downstream_headers(upstream_response.headers)
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=downstream_headers,
        media_type=None,
    )


async def forward_stream(
    request: Request,
    provider_url: str,
    api_key: str,
    provider_headers: dict[str, str] | None = None,
) -> tuple[Response | JSONResponse, dict[str, object]]:
    body = await request.body()
    headers = _build_upstream_headers(request, api_key, provider_headers)
    client = httpx.AsyncClient(timeout=None)
    try:
        upstream_request = client.build_request("POST", provider_url, content=body, headers=headers)
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": {"message": str(exc), "type": "upstream_error"}},
        ) from exc

    if upstream_response.status_code >= 400:
        error_response = await upstream_response.aread()
        await upstream_response.aclose()
        await client.aclose()
        fallback = httpx.Response(
            status_code=upstream_response.status_code,
            headers=upstream_response.headers,
            content=error_response,
        )
        return _upstream_error_response(fallback), {}

    state: dict[str, object] = {"usage": None, "upstream_id": None, "output_text": ""}

    async def stream_generator():
        pending = ""
        try:
            async for chunk in upstream_response.aiter_bytes():
                if chunk:
                    try:
                        pending += chunk.decode("utf-8")
                    except UnicodeDecodeError:
                        pending += chunk.decode("utf-8", errors="ignore")
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
                            if event.get("id") is not None:
                                state["upstream_id"] = str(event["id"])
                            if isinstance(event.get("usage"), dict):
                                state["usage"] = event["usage"]
                            choices = event.get("choices")
                            if isinstance(choices, list):
                                text_parts: list[str] = []
                                for choice in choices:
                                    if not isinstance(choice, dict):
                                        continue
                                    delta = choice.get("delta")
                                    if isinstance(delta, dict):
                                        text_parts.append(_extract_text_from_delta_content(delta.get("content")))
                                if text_parts:
                                    state["output_text"] = f"{state['output_text']}{''.join(text_parts)}"
                yield chunk
        finally:
            await upstream_response.aclose()
            await client.aclose()

    downstream_headers = _build_downstream_headers(upstream_response.headers)
    downstream_headers["Cache-Control"] = "no-cache"
    downstream_headers["X-Accel-Buffering"] = "no"
    return (
        StreamingResponse(
            stream_generator(),
            status_code=upstream_response.status_code,
            headers=downstream_headers,
            media_type=None,
        ),
        state,
    )
