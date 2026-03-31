# LEGACY_COMPONENT: LiteLLM model sync/probe integration has been removed from runtime paths.
from __future__ import annotations

from decimal import Decimal
import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ModelCatalog
from app.services.model_providers import build_litellm_model_name

logger = logging.getLogger(__name__)


def _litellm_model_info_id(model: ModelCatalog) -> str:
    return f"tokenmall-model-{model.id}"


def _litellm_payload(model: ModelCatalog) -> dict:
    return {
        "model_name": model.model_code,
        "litellm_params": {
            "model": build_litellm_model_name(model.provider, model.model_id),
            "api_base": settings.bailian_api_base,
            "api_key": settings.bailian_api_key,
            "input_cost_per_token": float(Decimal(model.input_price_per_million) / Decimal("1000000")),
            "output_cost_per_token": float(Decimal(model.output_price_per_million) / Decimal("1000000")),
        },
        "model_info": {
            "id": _litellm_model_info_id(model),
            "db_model": True,
            "base_model": model.model_id,
        },
    }


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    try:
        response = httpx.request(
            method,
            f"{settings.litellm_url}{path}",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json() if response.content else {}
    except httpx.HTTPStatusError as exc:
        detail = "LiteLLM 模型同步失败"
        try:
            data = exc.response.json()
            if isinstance(data, dict):
                detail = (
                    data.get("error", {}).get("message")
                    if isinstance(data.get("error"), dict)
                    else data.get("detail")
                    or data.get("message")
                    or detail
                )
        except Exception:  # noqa: BLE001
            detail = exc.response.text or detail
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LiteLLM 同步失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LiteLLM 服务不可用，无法同步模型配置",
        ) from exc


def _request_allowing_error(method: str, path: str, payload: dict | None = None) -> tuple[dict, int]:
    try:
        response = httpx.request(
            method,
            f"{settings.litellm_url}{path}",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )
        return (response.json() if response.content else {}, response.status_code)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LiteLLM 服务不可用，无法同步模型配置",
        ) from exc


def sync_model_to_litellm(model: ModelCatalog) -> None:
    payload = _litellm_payload(model)
    data, status_code = _request_allowing_error("POST", "/model/update", payload)
    if status_code < 400:
        return
    message = ""
    if isinstance(data, dict):
        error = data.get("error", {})
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        else:
            message = str(data.get("detail") or data.get("message") or "")
    if status_code in {400, 404} and ("model not found" in message.lower() or not message):
        _request("POST", "/model/new", payload)
        return
    if status_code >= 400:
        detail = message or "LiteLLM 模型同步失败"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LiteLLM 同步失败：{detail}")


def update_model_in_litellm(model: ModelCatalog) -> None:
    sync_model_to_litellm(model)


def delete_model_from_litellm(model: ModelCatalog) -> None:
    data, status_code = _request_allowing_error("POST", "/model/delete", {"id": _litellm_model_info_id(model)})
    if status_code < 400:
        return
    message = ""
    if isinstance(data, dict):
        error = data.get("error", {})
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        else:
            message = str(data.get("detail") or data.get("message") or "")
    if status_code == 404 or "not found" in message.lower():
        return
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LiteLLM 同步失败：{message or '模型删除失败'}")


def _probe_payload(model: ModelCatalog) -> tuple[str, dict] | None:
    capability_type = (model.capability_type or "chat").strip().lower()
    litellm_model_name = model.model_code
    if capability_type == "chat":
        return (
            "/v1/chat/completions",
            {
                "model": litellm_model_name,
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 1,
            },
        )
    if capability_type == "image":
        return (
            "/v1/images/generations",
            {
                "model": litellm_model_name,
                "prompt": "一张简洁的蓝色几何插画",
                "size": "1024x1024",
            },
        )
    if capability_type == "embedding":
        return (
            "/v1/embeddings",
            {
                "model": litellm_model_name,
                "input": "tokenmall model probe",
            },
        )
    return None


def sync_and_probe_model(model: ModelCatalog) -> None:
    try:
        sync_model_to_litellm(model)
        probe = _probe_payload(model)
        if probe is None:
            model.sync_status = "synced"
            model.sync_error = ""
            return
        path, payload = probe
        response = httpx.post(
            f"{settings.litellm_url}{path}",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        if response.is_success:
            model.sync_status = "ready"
            model.sync_error = ""
            return
        detail = response.text
        try:
            data = response.json()
            if isinstance(data, dict):
                detail = (
                    data.get("error", {}).get("message")
                    if isinstance(data.get("error"), dict)
                    else data.get("detail")
                    or data.get("message")
                    or detail
                )
        except Exception:  # noqa: BLE001
            pass
        model.sync_status = "error"
        model.sync_error = str(detail)[:1000]
    except HTTPException as exc:
        model.sync_status = "error"
        model.sync_error = str(exc.detail)[:1000]
    except Exception as exc:  # noqa: BLE001
        model.sync_status = "error"
        model.sync_error = str(exc)[:1000]


def sync_active_models_to_litellm() -> None:
    db = SessionLocal()
    try:
        all_models = db.query(ModelCatalog).all()
        for model in all_models:
            if model.is_active:
                sync_and_probe_model(model)
            else:
                try:
                    delete_model_from_litellm(model)
                except HTTPException:
                    pass
                model.sync_status = "disabled"
                model.sync_error = ""
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("LiteLLM active model sync failed: %s", exc)
    finally:
        db.close()
