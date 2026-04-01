from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    reserved_balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0.000000"), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="CNY", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="wallet")


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"
    __table_args__ = (
        UniqueConstraint("reference_type", "reference_id", "type", name="uq_wallet_ledger_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UsageReservation(Base):
    __tablename__ = "usage_reservations"
    __table_args__ = (
        Index("ix_usage_reservations_status_expires_at", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    model_code: Mapped[str] = mapped_column(String(120), nullable=False)
    reserved_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    actual_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    estimated_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    billing_source: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
