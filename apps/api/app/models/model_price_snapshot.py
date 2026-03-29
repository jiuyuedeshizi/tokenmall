from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ModelPriceSnapshot(Base):
    __tablename__ = "model_price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_catalog_id: Mapped[int] = mapped_column(ForeignKey("model_catalog.id", ondelete="CASCADE"), index=True, nullable=False)
    input_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    output_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
