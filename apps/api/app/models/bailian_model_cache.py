from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BailianModelCache(Base):
    __tablename__ = "bailian_model_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upstream_model_id: Mapped[str] = mapped_column(String(191), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="alibaba-bailian")
    provider_display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Alibaba Cloud")
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_code: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    capability_type: Mapped[str] = mapped_column(String(32), nullable=False, default="chat")
    billing_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="token")
    pricing_items: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    support_features: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="", nullable=False)
    input_price_per_million: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    output_price_per_million: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_source: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    owned_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
