from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ModelCatalog
from app.services.model_providers import build_litellm_model_name

router = APIRouter()


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def serialize_model(row: ModelCatalog):
    return {
        "id": row.id,
        "provider": row.provider,
        "litellm_model_name": build_litellm_model_name(row.provider, row.model_id or row.model_code),
        "vendor_display_name": row.vendor_display_name or row.provider,
        "model_code": row.model_code,
        "model_id": row.model_id or row.model_code,
        "capability_type": row.capability_type,
        "display_name": row.display_name,
        "category": row.category,
        "input_price_per_million": row.input_price_per_million,
        "output_price_per_million": row.output_price_per_million,
        "price_source": row.price_source,
        "last_price_synced_at": row.last_price_synced_at,
        "description": row.description,
        "hero_description": row.hero_description or row.description,
        "rating": row.rating,
        "support_features": split_csv(row.support_features) or ["多轮对话"],
        "tags": split_csv(row.tags) or [row.category],
        "example_python": row.example_python,
        "example_typescript": row.example_typescript,
        "example_curl": row.example_curl,
        "sync_status": row.sync_status,
        "sync_error": row.sync_error,
    }


@router.get("")
def list_models(db: Session = Depends(get_db)):
    rows = db.query(ModelCatalog).filter(ModelCatalog.is_active.is_(True)).order_by(ModelCatalog.id.asc()).all()
    return [serialize_model(row) for row in rows]


@router.get("/{model_code}")
def get_model_detail(model_code: str, db: Session = Depends(get_db)):
    row = (
        db.query(ModelCatalog)
        .filter(ModelCatalog.model_code == model_code, ModelCatalog.is_active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return serialize_model(row)


@router.get("/item/{model_id}")
def get_model_detail_by_id(model_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(ModelCatalog)
        .filter(ModelCatalog.id == model_id, ModelCatalog.is_active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return serialize_model(row)
