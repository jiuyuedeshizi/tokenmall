from decimal import Decimal, ROUND_HALF_UP

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


def calculate_usage_cost(model: ModelCatalog, prompt_tokens: int, completion_tokens: int) -> Decimal:
    input_cost = (Decimal(prompt_tokens) / Decimal("1000000")) * Decimal(model.input_price_per_million)
    output_cost = (Decimal(completion_tokens) / Decimal("1000000")) * Decimal(model.output_price_per_million)
    return (input_cost + output_cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
