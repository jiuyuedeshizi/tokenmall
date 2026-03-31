from decimal import Decimal, ROUND_HALF_UP
import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ModelCatalog

MODEL_ALIASES = {
    "qwen/qwen3.5-27b": "qwen-plus",
    "qwen/qwen-turbo": "qwen-turbo",
    "qwen/qwen-max-latest": "qwen-max",
}


def get_model_or_404(model_code: str, db: Session) -> ModelCatalog:
    normalized_code = (model_code or "").strip()
    resolved_code = MODEL_ALIASES.get(normalized_code, normalized_code)
    model = db.query(ModelCatalog).filter(ModelCatalog.model_code == resolved_code, ModelCatalog.is_active.is_(True)).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return model


def _parse_pricing_items(raw_value: str | None) -> list[dict]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _price_from_first_pricing_item(model: ModelCatalog) -> Decimal:
    items = _parse_pricing_items(model.pricing_items)
    if not items:
        return Decimal("0.0000")
    try:
        return Decimal(str(items[0].get("price") or "0"))
    except Exception:  # noqa: BLE001
        return Decimal("0.0000")


def resolve_per_second_unit_price(
    model: ModelCatalog,
    *,
    resolution: str | None = None,
    audio: bool | None = None,
) -> Decimal:
    items = _parse_pricing_items(model.pricing_items)
    if not items:
        return Decimal("0.0000")

    normalized_resolution = (resolution or "").strip().upper()
    expected_audio_keyword = None
    if audio is True:
        expected_audio_keyword = "有声"
    elif audio is False:
        expected_audio_keyword = "无声"

    if normalized_resolution or expected_audio_keyword:
        for item in items:
            label = str(item.get("label") or "")
            if normalized_resolution and normalized_resolution not in label.upper():
                continue
            if expected_audio_keyword and expected_audio_keyword not in label:
                continue
            try:
                return Decimal(str(item.get("price") or "0"))
            except Exception:  # noqa: BLE001
                return Decimal("0.0000")

    return _price_from_first_pricing_item(model)


def calculate_usage_cost(
    model: ModelCatalog,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    image_count: int = 0,
    char_count: int = 0,
    second_count: int = 0,
    resolution: str | None = None,
    audio: bool | None = None,
) -> Decimal:
    billing_mode = (model.billing_mode or "token").strip().lower()
    if billing_mode == "per_image":
        if image_count <= 0:
            return Decimal("0.0000")
        return (Decimal(image_count) * _price_from_first_pricing_item(model)).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )
    if billing_mode == "per_10k_chars":
        if char_count <= 0:
            return Decimal("0.0000")
        return ((Decimal(char_count) / Decimal("10000")) * _price_from_first_pricing_item(model)).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )
    if billing_mode == "per_second":
        if second_count <= 0:
            return Decimal("0.0000")
        unit_price = resolve_per_second_unit_price(model, resolution=resolution, audio=audio)
        return (Decimal(second_count) * unit_price).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )
    if billing_mode != "token":
        return Decimal("0.0000")
    input_cost = (Decimal(prompt_tokens) / Decimal("1000000")) * Decimal(model.input_price_per_million)
    output_cost = (Decimal(completion_tokens) / Decimal("1000000")) * Decimal(model.output_price_per_million)
    return (input_cost + output_cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
