import json
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import get_api_key_entity
from app.db.session import get_db
from app.models import User
from app.providers import get_bailian_provider_config
from app.services.proxy import (
    after_estimated_character_response,
    after_response,
    before_request,
    forward_request,
    forward_stream,
    on_error,
)
from app.services.routing import (
    build_bailian_task_status_url,
    resolve_bailian_multimodal_generation_route,
    resolve_bailian_video_synthesis_route,
)

router = APIRouter()


def _extract_image_generation_usage(response_payload: dict) -> dict:
    usage = response_payload.get("usage")
    if isinstance(usage, dict):
        return usage

    output = response_payload.get("output")
    if not isinstance(output, dict):
        return {}

    results = output.get("results")
    if isinstance(results, list):
        return {"image_count": len(results)}
    result_urls = output.get("result_urls")
    if isinstance(result_urls, list):
        return {"image_count": len(result_urls)}
    return {}


def _extract_bailian_usage(response_payload: dict, model, payload: dict) -> dict:
    image_usage = _extract_image_generation_usage(response_payload)
    if image_usage:
        return image_usage

    billing_mode = (getattr(model, "billing_mode", None) or "token").strip().lower()
    if billing_mode == "per_image":
        return {"image_count": 1}
    if billing_mode == "per_10k_chars":
        input_payload = payload.get("input")
        if isinstance(input_payload, dict) and isinstance(input_payload.get("text"), str):
            return {"char_count": len(input_payload["text"])}
    usage = response_payload.get("usage")
    return usage if isinstance(usage, dict) else {}


def _extract_video_usage_from_payload(payload: dict) -> dict:
    parameters = payload.get("parameters")
    parameters = parameters if isinstance(parameters, dict) else {}
    input_payload = payload.get("input")
    input_payload = input_payload if isinstance(input_payload, dict) else {}

    try:
        second_count = max(0, int(parameters.get("duration") or 0))
    except (TypeError, ValueError):
        second_count = 0

    resolution = str(parameters.get("resolution") or "1080P").strip().upper()
    audio = parameters.get("audio")
    if audio is False:
        audio_enabled = False
    elif isinstance(audio, bool):
        audio_enabled = audio
    else:
        audio_enabled = bool(input_payload.get("audio_url")) or True

    return {
        "second_count": second_count,
        "resolution": resolution,
        "audio": audio_enabled,
    }


def _resolve_request_identity(api_key, db: Session):
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


@router.post("/api/v1/services/aigc/multimodal-generation/generation")
async def bailian_multimodal_generation(
    request: Request,
    api_key=Depends(get_api_key_entity),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是合法 JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是 JSON 对象")

    user = _resolve_request_identity(api_key, db)

    route_target = resolve_bailian_multimodal_generation_route(str(payload.get("model", "")), db)
    request_id = before_request(api_key=api_key, user=user, payload=payload, model=route_target.model, db=db)
    stream_enabled = request.headers.get("x-dashscope-sse", "").strip().lower() == "enable"
    started_at = perf_counter()

    if stream_enabled:
        try:
            proxy_response, stream_state = await forward_stream(
                request=request,
                provider_url=route_target.provider_url,
                api_key=route_target.provider_api_key,
                provider_headers=route_target.provider_headers,
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
                error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
                response_time_ms=response_time_ms,
                db=db,
            )
            return proxy_response

        async def finalize_stream():
            response_time_ms = int((perf_counter() - started_at) * 1000)
            try:
                usage = stream_state.get("usage")
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
                if (route_target.model.billing_mode or "").strip().lower() == "per_10k_chars":
                    after_estimated_character_response(
                        api_key=api_key,
                        user=user,
                        model=route_target.model,
                        request_id=request_id,
                        payload=payload,
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

    try:
        proxy_response = await forward_request(
            request=request,
            provider_url=route_target.provider_url,
            api_key=route_target.provider_api_key,
            provider_headers=route_target.provider_headers,
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
            error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
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
            response_payload={
                "id": response_payload.get("request_id", request_id),
                "usage": _extract_bailian_usage(response_payload, route_target.model, payload),
            },
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="上游响应缺少可结算 usage") from exc
    return proxy_response


@router.post("/api/v1/services/aigc/video-generation/video-synthesis")
async def bailian_video_synthesis(
    request: Request,
    api_key=Depends(get_api_key_entity),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是合法 JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是 JSON 对象")

    user = _resolve_request_identity(api_key, db)
    route_target = resolve_bailian_video_synthesis_route(str(payload.get("model", "")), db)
    request_id = before_request(api_key=api_key, user=user, payload=payload, model=route_target.model, db=db)
    started_at = perf_counter()

    try:
        proxy_response = await forward_request(
            request=request,
            provider_url=route_target.provider_url,
            api_key=route_target.provider_api_key,
            provider_headers=route_target.provider_headers,
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
            error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
            response_time_ms=response_time_ms,
            db=db,
        )
        return proxy_response

    response_time_ms = int((perf_counter() - started_at) * 1000)
    try:
        response_payload = json.loads(proxy_response.body.decode("utf-8"))
        if not isinstance(response_payload, dict):
            raise ValueError("响应体必须是 JSON 对象")
        output = response_payload.get("output")
        output = output if isinstance(output, dict) else {}
        after_response(
            api_key=api_key,
            user=user,
            model=route_target.model,
            request_id=request_id,
            response_payload={
                "id": output.get("task_id") or response_payload.get("request_id") or request_id,
                "usage": _extract_video_usage_from_payload(payload),
            },
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="上游响应缺少可结算 usage") from exc
    return proxy_response


@router.get("/api/v1/tasks/{task_id}")
async def bailian_task_status(
    task_id: str,
    request: Request,
    api_key=Depends(get_api_key_entity),
    db: Session = Depends(get_db),
):
    _resolve_request_identity(api_key, db)
    provider_config = get_bailian_provider_config()
    provider_url = build_bailian_task_status_url(task_id)
    return await forward_request(
        request=request,
        provider_url=provider_url,
        api_key=provider_config.api_key,
        provider_headers=provider_config.headers,
        method="GET",
    )
