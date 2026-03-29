from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey, PaymentOrder, UsageReservation, User, WalletAccount, WalletLedger


def get_wallet_account(user_id: int, db: Session) -> WalletAccount:
    account = db.query(WalletAccount).filter(WalletAccount.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="钱包不存在")
    return account


def get_available_balance(account: WalletAccount) -> Decimal:
    return Decimal(account.balance) - Decimal(account.reserved_balance)


def create_payment_order(user: User, amount: Decimal, payment_method: str, db: Session) -> PaymentOrder:
    order = PaymentOrder(
        order_no=f"ord{uuid4().hex[:18]}",
        user_id=user.id,
        amount=amount,
        payment_method=payment_method,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_payment_order_channel(
    order: PaymentOrder,
    *,
    channel_order_no: str | None,
    payment_url: str | None,
    qr_code: str | None,
    qr_code_image: str | None,
    db: Session,
) -> PaymentOrder:
    order.channel_order_no = channel_order_no
    order.payment_url = payment_url
    order.qr_code = qr_code
    order.qr_code_image = qr_code_image
    db.commit()
    db.refresh(order)
    return order


def apply_balance_change(
    user_id: int,
    amount: Decimal,
    ledger_type: str,
    reference_type: str,
    reference_id: str,
    description: str,
    db: Session,
) -> WalletAccount:
    account = get_wallet_account(user_id, db)
    next_balance = Decimal(account.balance) + Decimal(amount)
    if next_balance < Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="余额不足")

    account.balance = next_balance
    ledger = WalletLedger(
        user_id=user_id,
        type=ledger_type,
        amount=amount,
        balance_after=next_balance,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )
    db.add(ledger)
    db.flush()
    return account


def create_usage_reservation(
    *,
    user_id: int,
    api_key: ApiKey,
    model_code: str,
    request_id: str,
    reserved_amount: Decimal,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    db: Session,
) -> UsageReservation:
    account = db.execute(
        select(WalletAccount).where(WalletAccount.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="钱包不存在")

    available_balance = get_available_balance(account)
    if available_balance < reserved_amount:
        api_key.status = "arrears"
        db.commit()
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="可用余额不足以覆盖本次请求")

    account.reserved_balance = Decimal(account.reserved_balance) + reserved_amount
    reservation = UsageReservation(
        user_id=user_id,
        api_key_id=api_key.id,
        request_id=request_id,
        model_code=model_code,
        reserved_amount=reserved_amount,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def release_usage_reservation(
    *,
    request_id: str,
    error_message: str,
    db: Session,
) -> UsageReservation | None:
    reservation = db.execute(
        select(UsageReservation).where(UsageReservation.request_id == request_id).with_for_update()
    ).scalar_one_or_none()
    if not reservation or reservation.status != "pending":
        return reservation

    account = db.execute(
        select(WalletAccount).where(WalletAccount.user_id == reservation.user_id).with_for_update()
    ).scalar_one()
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "failed"
    reservation.error_message = error_message[:255]
    db.commit()
    db.refresh(reservation)
    return reservation


def capture_usage_reservation(
    *,
    request_id: str,
    actual_amount: Decimal,
    description: str,
    reference_id: str,
    db: Session,
) -> tuple[UsageReservation, WalletAccount]:
    reservation = db.execute(
        select(UsageReservation).where(UsageReservation.request_id == request_id).with_for_update()
    ).scalar_one_or_none()
    if not reservation or reservation.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预占记录不存在")

    account = db.execute(
        select(WalletAccount).where(WalletAccount.user_id == reservation.user_id).with_for_update()
    ).scalar_one()

    if Decimal(account.balance) < actual_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算失败：余额不足")

    account.balance = Decimal(account.balance) - actual_amount
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "captured"
    reservation.actual_amount = actual_amount

    db.add(
        WalletLedger(
            user_id=reservation.user_id,
            type="consume",
            amount=-actual_amount,
            balance_after=Decimal(account.balance),
            reference_type="usage_log",
            reference_id=reference_id,
            description=description,
        )
    )
    db.commit()
    db.refresh(reservation)
    db.refresh(account)
    return reservation, account


def mark_order_paid(order_no: str, db: Session, description: str = "充值到账") -> PaymentOrder:
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order.status == "paid":
        return order

    apply_balance_change(
        user_id=order.user_id,
        amount=Decimal(order.amount),
        ledger_type="recharge",
        reference_type="payment_order",
        reference_id=order.order_no,
        description=description,
        db=db,
    )
    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order
