import json
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.api.deps import get_api_key_entity_async
from app.db.session import AsyncSessionLocal, get_async_db
from app.models import User
from app.providers import get_bailian_provider_config
from app.services.proxy import (
    after_estimated_character_response_async,
    after_response_async,
    before_request_async,
    forward_request,
    forward_stream,
    on_error_async,
)
from app.services.routing import (
    build_bailian_task_status_url,
    resolve_bailian_multimodal_generation_route_async,
    resolve_bailian_video_synthesis_route_async,
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


async def _resolve_request_identity(api_key, db: AsyncSession):
    user = (await db.execute(select(User).where(User.id == api_key.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


@router.post("/api/v1/services/aigc/multimodal-generation/generation")
async def bailian_multimodal_generation(
    request: Request,
    api_key=Depends(get_api_key_entity_async),
    db: AsyncSession = Depends(get_async_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是合法 JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是 JSON 对象")

    user = await _resolve_request_identity(api_key, db)

    route_target = await resolve_bailian_multimodal_generation_route_async(str(payload.get("model", "")), db)
    request_id = await before_request_async(api_key=api_key, user=user, payload=payload, model=route_target.model, db=db)
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
            async with AsyncSessionLocal() as error_db:
                await on_error_async(
                    api_key=api_key,
                    user=user,
                    request_id=request_id,
                    model_code=route_target.model.model_code,
                    error_message=str(exc),
                    response_time_ms=response_time_ms,
                    db=error_db,
                )
            raise

        if isinstance(proxy_response, JSONResponse) and proxy_response.status_code >= 400:
            response_time_ms = int((perf_counter() - started_at) * 1000)
            body = json.loads(proxy_response.body.decode("utf-8"))
            async with AsyncSessionLocal() as error_db:
                await on_error_async(
                    api_key=api_key,
                    user=user,
                    request_id=request_id,
                    model_code=route_target.model.model_code,
                    error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
                    response_time_ms=response_time_ms,
                    db=error_db,
                )
            return proxy_response

        async def finalize_stream():
            response_time_ms = int((perf_counter() - started_at) * 1000)
            try:
                usage = stream_state.get("usage")
                if isinstance(usage, dict):
                    async with AsyncSessionLocal() as success_db:
                        await after_response_async(
                            api_key=api_key,
                            user=user,
                            model=route_target.model,
                            request_id=request_id,
                            response_payload={
                                "id": stream_state.get("upstream_id") or request_id,
                                "usage": usage,
                            },
                            response_time_ms=response_time_ms,
                            db=success_db,
                        )
                    return
                if (route_target.model.billing_mode or "").strip().lower() == "per_10k_chars":
                    async with AsyncSessionLocal() as success_db:
                        await after_estimated_character_response_async(
                            api_key=api_key,
                            user=user,
                            model=route_target.model,
                            request_id=request_id,
                            payload=payload,
                            upstream_id=str(stream_state.get("upstream_id") or request_id),
                            response_time_ms=response_time_ms,
                            db=success_db,
                        )
                    return
                async with AsyncSessionLocal() as error_db:
                    await on_error_async(
                        api_key=api_key,
                        user=user,
                        request_id=request_id,
                        model_code=route_target.model.model_code,
                        error_message="流式响应未返回 usage 数据",
                        response_time_ms=response_time_ms,
                        db=error_db,
                    )
            except Exception as exc:  # noqa: BLE001
                async with AsyncSessionLocal() as error_db:
                    await on_error_async(
                        api_key=api_key,
                        user=user,
                        request_id=request_id,
                        model_code=route_target.model.model_code,
                        error_message=str(exc),
                        response_time_ms=response_time_ms,
                        db=error_db,
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
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        raise

    if isinstance(proxy_response, JSONResponse) and proxy_response.status_code >= 400:
        response_time_ms = int((perf_counter() - started_at) * 1000)
        body = json.loads(proxy_response.body.decode("utf-8"))
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        return proxy_response

    response_time_ms = int((perf_counter() - started_at) * 1000)
    try:
        response_payload = json.loads(proxy_response.body.decode("utf-8"))
        if not isinstance(response_payload, dict):
            raise ValueError("响应体必须是 JSON 对象")
        async with AsyncSessionLocal() as success_db:
            await after_response_async(
                api_key=api_key,
                user=user,
                model=route_target.model,
                request_id=request_id,
                response_payload={
                    "id": response_payload.get("request_id", request_id),
                    "usage": _extract_bailian_usage(response_payload, route_target.model, payload),
                },
                response_time_ms=response_time_ms,
                db=success_db,
            )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="上游响应缺少可结算 usage") from exc
    return proxy_response


@router.post("/api/v1/services/aigc/video-generation/video-synthesis")
async def bailian_video_synthesis(
    request: Request,
    api_key=Depends(get_api_key_entity_async),
    db: AsyncSession = Depends(get_async_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是合法 JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请求体必须是 JSON 对象")

    user = await _resolve_request_identity(api_key, db)
    route_target = await resolve_bailian_video_synthesis_route_async(str(payload.get("model", "")), db)
    request_id = await before_request_async(api_key=api_key, user=user, payload=payload, model=route_target.model, db=db)
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
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        raise

    if isinstance(proxy_response, JSONResponse) and proxy_response.status_code >= 400:
        response_time_ms = int((perf_counter() - started_at) * 1000)
        body = json.loads(proxy_response.body.decode("utf-8"))
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(body.get("error", {}).get("message") or body.get("message") or "模型服务调用失败"),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        return proxy_response

    response_time_ms = int((perf_counter() - started_at) * 1000)
    try:
        response_payload = json.loads(proxy_response.body.decode("utf-8"))
        if not isinstance(response_payload, dict):
            raise ValueError("响应体必须是 JSON 对象")
        output = response_payload.get("output")
        output = output if isinstance(output, dict) else {}
        async with AsyncSessionLocal() as success_db:
            await after_response_async(
                api_key=api_key,
                user=user,
                model=route_target.model,
                request_id=request_id,
                response_payload={
                    "id": output.get("task_id") or response_payload.get("request_id") or request_id,
                    "usage": _extract_video_usage_from_payload(payload),
                },
                response_time_ms=response_time_ms,
                db=success_db,
            )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as error_db:
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id=request_id,
                model_code=route_target.model.model_code,
                error_message=str(exc),
                response_time_ms=response_time_ms,
                db=error_db,
            )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="上游响应缺少可结算 usage") from exc
    return proxy_response


@router.get("/api/v1/tasks/{task_id}")
async def bailian_task_status(
    task_id: str,
    request: Request,
    api_key=Depends(get_api_key_entity_async),
    db: AsyncSession = Depends(get_async_db),
):
    await _resolve_request_identity(api_key, db)
    provider_config = get_bailian_provider_config()
    provider_url = build_bailian_task_status_url(task_id)
    return await forward_request(
        request=request,
        provider_url=provider_url,
        api_key=provider_config.api_key,
        provider_headers=provider_config.headers,
        method="GET",
    )
