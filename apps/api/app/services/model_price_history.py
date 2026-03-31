from __future__ import annotations

from decimal import Decimal

from app.models import ModelCatalog, ModelPriceSnapshot


def create_price_snapshot(
    *,
    model: ModelCatalog,
    note: str,
    db,
) -> ModelPriceSnapshot:
    snapshot = ModelPriceSnapshot(
        model_catalog_id=model.id,
        input_price_per_million=Decimal(model.input_price_per_million),
        output_price_per_million=Decimal(model.output_price_per_million),
        note=note,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def create_price_snapshot_if_changed(
    *,
    model: ModelCatalog,
    old_input_price: Decimal,
    old_output_price: Decimal,
    note: str,
    db,
) -> ModelPriceSnapshot | None:
    if Decimal(model.input_price_per_million) == Decimal(old_input_price) and Decimal(model.output_price_per_million) == Decimal(old_output_price):
        return None
    return create_price_snapshot(model=model, note=note, db=db)
