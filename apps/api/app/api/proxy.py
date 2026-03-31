import json
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import get_api_key_entity
from app.db.session import get_db
from app.models import User
from app.services.proxy import (
    after_estimated_stream_response,
    after_response,
    before_request,
    forward_request,
    forward_stream,
    on_error,
)
from app.services.routing import resolve_chat_route

router = APIRouter()


def _build_upstream_payload_bytes(payload: dict, upstream_model_id: str) -> bytes | None:
    if not upstream_model_id:
        return None
    if str(payload.get("model", "")) == upstream_model_id:
        return None
    upstream_payload = dict(payload)
    upstream_payload["model"] = upstream_model_id
    return json.dumps(upstream_payload, ensure_ascii=False).encode("utf-8")


@router.post("/chat/completions")
async def create_chat_completion(
    request: Request,
    api_key=Depends(get_api_key_entity),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"message": "请求体必须是合法 JSON", "type": "invalid_request_error"}},
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"message": "请求体必须是 JSON 对象", "type": "invalid_request_error"}},
        )

    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "用户不存在", "type": "invalid_api_key"}},
        )

    route_target = resolve_chat_route(str(payload.get("model", "")), db)
    request_id = before_request(api_key=api_key, user=user, payload=payload, model=route_target.model, db=db)
    stream_enabled = bool(payload.get("stream"))
    body_override = _build_upstream_payload_bytes(
        payload,
        getattr(route_target, "upstream_model_id", str(payload.get("model", ""))),
    )
    started_at = perf_counter()

    if not stream_enabled:
        try:
            proxy_response = await forward_request(
                request=request,
                provider_url=route_target.provider_url,
                api_key=route_target.provider_api_key,
                provider_headers=route_target.provider_headers,
                body_override=body_override,
            )
        except Exception as exc:  # noqa: BLE001
            response_time_ms = int((perf_counter() - started_at) * 1000)
            on_error(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=db,
            )
            raise

        if isinstance(proxy_response, JSONResponse) and proxy_response.status_code >= 400:
            response_time_ms = int((perf_counter() - started_at) * 1000)
            body = json.loads(proxy_response.body.decode("utf-8"))
            on_error(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(body.get("error", {}).get("message") or "模型服务调用失败"),
                response_time_ms=response_time_ms,
                db=db,
            )
            return proxy_response

        response_time_ms = int((perf_counter() - started_at) * 1000)
        try:
            response_payload = json.loads(proxy_response.body.decode("utf-8"))
            if not isinstance(response_payload, dict):
                raise ValueError("响应体必须是 JSON 对象")
            after_response(
                api_key=api_key,
                user=user,
                model=route_target.model,
                request_id=request_id,
                response_payload=response_payload,
                response_time_ms=response_time_ms,
                db=db,
            )
        except Exception as exc:  # noqa: BLE001
            on_error(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=db,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": {"message": "上游响应缺少可结算 usage", "type": "upstream_error"}},
            ) from exc
        return proxy_response

    try:
        proxy_response, stream_state = await forward_stream(
            request=request,
            provider_url=route_target.provider_url,
            api_key=route_target.provider_api_key,
            provider_headers=route_target.provider_headers,
            body_override=body_override,
        )
    except Exception as exc:  # noqa: BLE001
        response_time_ms = int((perf_counter() - started_at) * 1000)
        on_error(
            api_key=api_key,
            user=user,
            request_id=request_id,
            model_code=route_target.model.model_code,
            error_message=str(exc),
            response_time_ms=response_time_ms,
            db=db,
        )
        raise

    if isinstance(proxy_response, JSONResponse) and proxy_response.status_code >= 400:
        response_time_ms = int((perf_counter() - started_at) * 1000)
        body = json.loads(proxy_response.body.decode("utf-8"))
        on_error(
            api_key=api_key,
            user=user,
            request_id=request_id,
            model_code=route_target.model.model_code,
            error_message=str(body.get("error", {}).get("message") or "模型服务调用失败"),
            response_time_ms=response_time_ms,
            db=db,
        )
        return proxy_response

    async def finalize_stream():
        response_time_ms = int((perf_counter() - started_at) * 1000)
        usage = stream_state.get("usage")
        try:
            if isinstance(usage, dict):
                after_response(
                    api_key=api_key,
                    user=user,
                    model=route_target.model,
                    request_id=request_id,
                    response_payload={
                        "id": stream_state.get("upstream_id") or request_id,
                        "usage": usage,
                    },
                    response_time_ms=response_time_ms,
                    db=db,
                )
                return
            if (route_target.provider_name or "").strip().lower() in {"alibaba-bailian", "dashscope"}:
                after_estimated_stream_response(
                    api_key=api_key,
                    user=user,
                    model=route_target.model,
                    request_id=request_id,
                    payload=payload,
                    output_text=str(stream_state.get("output_text") or ""),
                    upstream_id=str(stream_state.get("upstream_id") or request_id),
                    response_time_ms=response_time_ms,
                    db=db,
                )
                return
            on_error(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message="流式响应未返回 usage 数据",
                response_time_ms=response_time_ms,
                db=db,
            )
        except Exception as exc:  # noqa: BLE001
            on_error(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=db,
            )

    proxy_response.background = BackgroundTask(finalize_stream)
    return proxy_response
