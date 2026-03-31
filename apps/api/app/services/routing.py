from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ModelCatalog
from app.providers import get_bailian_provider_config, get_tencent_provider_config


@dataclass(frozen=True)
class RouteTarget:
    provider_name: str
    provider_url: str
    provider_api_key: str
    provider_headers: dict[str, str]
    upstream_model_id: str
    model: ModelCatalog


def _build_provider_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _resolve_provider(model: ModelCatalog) -> tuple[str, str, dict[str, str]]:
    normalized_provider = (model.provider or "").strip().lower()
    if normalized_provider in {"alibaba-bailian", "dashscope"}:
        config = get_bailian_provider_config()
        return config.base_url, config.api_key, dict(config.headers)
    if normalized_provider == "tencent":
        config = get_tencent_provider_config()
        if config.base_url or config.api_key:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="腾讯 provider 当前为预留配置，尚未启用",
            )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="腾讯 provider 当前为预留配置，尚未启用",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"暂不支持 provider: {model.provider}",
    )


def resolve_chat_route(model_code: str, db: Session) -> RouteTarget:
    normalized_code = (model_code or "").strip()
    if not normalized_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 model")

    model = (
        db.query(ModelCatalog)
        .filter(ModelCatalog.model_code == normalized_code, ModelCatalog.is_active.is_(True))
        .first()
    )
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")

    upstream_model_id = (model.model_id or "").strip()
    if not upstream_model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型未配置上游 model_id")
    if normalized_code != upstream_model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前透明代理要求 model_code 与上游 model_id 完全一致",
        )

    base_url, api_key, headers = _resolve_provider(model)
    if not base_url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="上游 provider base_url 未配置")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="上游 provider api_key 未配置")

    return RouteTarget(
        provider_name=model.provider,
        provider_url=_build_provider_url(base_url, "/chat/completions"),
        provider_api_key=api_key,
        provider_headers=headers,
        upstream_model_id=upstream_model_id,
        model=model,
    )
