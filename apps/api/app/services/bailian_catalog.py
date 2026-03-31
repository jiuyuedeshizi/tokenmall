from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import re

import httpx

from app.core.config import settings
from app.models import BailianModelCache, ModelCatalog
from app.services.official_model_catalog import get_official_model_metadata


PROVIDER_LABEL_MAP = {
    "qwen": ("alibaba-bailian", "Alibaba"),
    "wanx": ("alibaba-bailian", "Alibaba"),
    "cosyvoice": ("alibaba-bailian", "Alibaba"),
    "paraformer": ("alibaba-bailian", "Alibaba"),
    "sambert": ("alibaba-bailian", "Alibaba"),
    "minimax": ("minimax", "MiniMax"),
    "siliconflow": ("siliconflow", "SiliconFlow"),
    "deepseek": ("deepseek", "DeepSeek"),
    "moonshot": ("moonshot", "Moonshot"),
    "glm": ("glm", "智谱"),
}


def normalize_platform_model_code(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "-").replace("/", "-")
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-._")
    if not normalized:
        normalized = "model"
    if not normalized[0].isalnum():
        normalized = f"m-{normalized}"
    return normalized[:120]


def infer_capability(model_id: str) -> tuple[str, str]:
    lower = model_id.lower()
    if "embedding" in lower or "rerank" in lower:
        return ("embedding", "text")
    if "image" in lower or "wanx" in lower:
        return ("image", "image")
    if any(keyword in lower for keyword in ["speech", "audio", "tts", "asr", "paraformer", "cosyvoice", "sambert"]):
        return ("audio", "audio")
    if "video" in lower:
        return ("video", "video")
    return ("chat", "text")


def infer_provider(model_id: str) -> tuple[str, str]:
    if "/" in model_id:
        prefix = model_id.split("/", 1)[0].strip().lower()
        return PROVIDER_LABEL_MAP.get(prefix, (prefix, prefix.title()))
    base = model_id.split("-", 1)[0].strip().lower()
    return PROVIDER_LABEL_MAP.get(base, ("alibaba-bailian", "Alibaba"))


def prettify_display_name(model_id: str) -> str:
    if "/" in model_id:
        _, model_id = model_id.split("/", 1)
    return model_id.replace("-", " ").replace("_", " ").title().replace("Qwen", "Qwen").replace("Glm", "GLM")


def build_cache_payload(raw_item: dict) -> dict:
    upstream_model_id = str(raw_item.get("id") or "").strip()
    provider, provider_display_name = infer_provider(upstream_model_id)
    capability_type, category = infer_capability(upstream_model_id)
    base_model_id = upstream_model_id.split("/", 1)[-1]
    official_metadata = get_official_model_metadata(base_model_id) or {}
    display_name = str(official_metadata.get("display_name") or prettify_display_name(upstream_model_id))
    return {
        "upstream_model_id": upstream_model_id,
        "provider": str(official_metadata.get("provider") or provider),
        "provider_display_name": str(official_metadata.get("vendor_display_name") or provider_display_name),
        "display_name": display_name,
        "model_code": normalize_platform_model_code(base_model_id),
        "category": str(official_metadata.get("category") or category),
        "capability_type": str(official_metadata.get("capability_type") or capability_type),
        "description": str(official_metadata.get("description") or ""),
        "support_features": str(official_metadata.get("support_features") or {
            "chat": "多轮对话,知识问答,工具调用",
            "image": "图像生成,创意设计,高质量输出",
            "embedding": "向量检索,知识库召回,文本嵌入",
            "audio": "语音合成,语音识别,音频处理",
            "video": "视频生成,多模态理解",
        }.get(capability_type, "")),
        "tags": str(official_metadata.get("tags") or ""),
        "billing_mode": str(official_metadata.get("billing_mode") or "token"),
        "pricing_items": str(official_metadata.get("pricing_items") or "[]"),
        "input_price_per_million": official_metadata.get("input_price_per_million"),
        "output_price_per_million": official_metadata.get("output_price_per_million"),
        "owned_by": str(raw_item.get("owned_by") or ""),
        "raw_payload": json.dumps(raw_item, ensure_ascii=False),
        "is_available": True,
        "last_synced_at": datetime.now(timezone.utc),
    }


async def fetch_bailian_models() -> list[dict]:
    async with httpx.AsyncClient(timeout=40.0) as client:
        response = await client.get(
            f"{settings.bailian_api_base.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {settings.bailian_api_key}"},
        )
        response.raise_for_status()
        data = response.json()
    return data.get("data", []) if isinstance(data, dict) else []


def upsert_bailian_cache(db, items: list[dict]) -> list[BailianModelCache]:
    caches: list[BailianModelCache] = []
    existing = {
        row.upstream_model_id: row
        for row in db.query(BailianModelCache).all()
    }
    seen_ids: set[str] = set()
    for item in items:
        payload = build_cache_payload(item)
        seen_ids.add(payload["upstream_model_id"])
        row = existing.get(payload["upstream_model_id"])
        if row is None:
            row = BailianModelCache(**payload)
            db.add(row)
        else:
            for key, value in payload.items():
                setattr(row, key, value)
        caches.append(row)
    for upstream_id, row in existing.items():
        if upstream_id not in seen_ids:
            row.is_available = False
            row.last_synced_at = datetime.now(timezone.utc)
    db.flush()
    return caches


def import_bailian_models(db, upstream_ids: list[str]) -> list[ModelCatalog]:
    rows = (
        db.query(BailianModelCache)
        .filter(BailianModelCache.upstream_model_id.in_(upstream_ids))
        .all()
    )
    imported: list[ModelCatalog] = []
    for row in rows:
        existing = db.query(ModelCatalog).filter(ModelCatalog.model_code == row.model_code).first()
        if existing:
            existing.provider = row.provider
            existing.model_id = row.upstream_model_id
            existing.capability_type = row.capability_type
            existing.display_name = row.display_name
            existing.vendor_display_name = row.provider_display_name
            existing.category = row.category
            if row.description:
                existing.description = row.description
                existing.hero_description = row.description
            if row.support_features:
                existing.support_features = row.support_features
            if row.tags:
                existing.tags = row.tags
            imported.append(existing)
            continue
        model = ModelCatalog(
            provider=row.provider,
            model_code=row.model_code,
            model_id=row.upstream_model_id,
            capability_type=row.capability_type,
            display_name=row.display_name,
            vendor_display_name=row.provider_display_name,
            category=row.category,
            billing_mode=row.billing_mode or "token",
            pricing_items=row.pricing_items or "[]",
            input_price_per_million=row.input_price_per_million or Decimal("0.0000"),
            output_price_per_million=row.output_price_per_million or Decimal("0.0000"),
            description=row.description,
            hero_description=row.description,
            support_features=row.support_features,
            tags=row.tags,
            is_active=True,
        )
        db.add(model)
        imported.append(model)
    db.flush()
    return imported


def sync_prices_from_bailian_cache(db) -> int:
    return 0
