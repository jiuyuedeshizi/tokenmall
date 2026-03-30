from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ModelCatalog(Base):
    __tablename__ = "model_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_code: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    model_id: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    capability_type: Mapped[str] = mapped_column(String(32), default="chat", nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    vendor_display_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_mode: Mapped[str] = mapped_column(String(32), default="token", nullable=False)
    pricing_items: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    input_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    output_price_per_million: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price_source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    last_price_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rating: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("4.80"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hero_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    support_features: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", nullable=False)
    example_python: Mapped[str] = mapped_column(Text, default="", nullable=False)
    example_typescript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    example_curl: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sync_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    sync_error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
