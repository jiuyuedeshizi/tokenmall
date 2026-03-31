from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models import ApiKey, PaymentOrder, UsageReservation, User, WalletAccount, WalletLedger
from app.services.observability import increment_metric, log_event


def get_wallet_account(user_id: int, db: Session) -> WalletAccount:
    account = db.query(WalletAccount).filter(WalletAccount.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="钱包不存在")
    return account


async def get_wallet_account_async(user_id: int, db: AsyncSession) -> WalletAccount:
    account = (
        await db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id))
    ).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="钱包不存在")
    return account


def lock_wallet_account(user_id: int, db: Session) -> WalletAccount:
    account = (
        db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id).with_for_update()).scalar_one_or_none()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="钱包不存在")
    return account


async def lock_wallet_account_async(user_id: int, db: AsyncSession) -> WalletAccount:
    account = (
        await db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id).with_for_update())
    ).scalar_one_or_none()
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


def _apply_locked_balance_change(
    *,
    account: WalletAccount,
    user_id: int,
    amount: Decimal,
    ledger_type: str,
    reference_type: str,
    reference_id: str,
    description: str,
    db: Session | AsyncSession,
) -> WalletAccount:
    next_balance = Decimal(account.balance) + Decimal(amount)
    if next_balance < Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="余额不足")

    account.balance = next_balance
    db.add(
        WalletLedger(
            user_id=user_id,
            type=ledger_type,
            amount=amount,
            balance_after=next_balance,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
        )
    )
    return account


def apply_balance_change(
    user_id: int,
    amount: Decimal,
    ledger_type: str,
    reference_type: str,
    reference_id: str,
    description: str,
    db: Session,
) -> WalletAccount:
    account = lock_wallet_account(user_id, db)
    try:
        _apply_locked_balance_change(
            account=account,
            user_id=user_id,
            amount=amount,
            ledger_type=ledger_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            db=db,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        account = get_wallet_account(user_id, db)
    else:
        db.refresh(account)
    return account


async def apply_balance_change_async(
    *,
    user_id: int,
    amount: Decimal,
    ledger_type: str,
    reference_type: str,
    reference_id: str,
    description: str,
    db: AsyncSession,
    commit: bool = True,
) -> WalletAccount:
    account = await lock_wallet_account_async(user_id, db)
    _apply_locked_balance_change(
        account=account,
        user_id=user_id,
        amount=amount,
        ledger_type=ledger_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        db=db,
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return await get_wallet_account_async(user_id, db)
    if commit:
        await db.commit()
        await db.refresh(account)
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
    billing_source: str = "reserved_estimate",
    db: Session,
) -> UsageReservation:
    account = lock_wallet_account(user_id, db)

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
        billing_source=billing_source,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    increment_metric("reservation.created_total")
    log_event(
        "reservation.created",
        user_id=user_id,
        api_key_id=api_key.id,
        request_id=request_id,
        model_code=model_code,
        reserved_amount=reserved_amount,
        status=reservation.status,
    )
    return reservation


async def create_usage_reservation_async(
    *,
    user_id: int,
    api_key: ApiKey,
    model_code: str,
    request_id: str,
    reserved_amount: Decimal,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    billing_source: str = "reserved_estimate",
    db: AsyncSession,
) -> UsageReservation:
    account = await lock_wallet_account_async(user_id, db)
    available_balance = get_available_balance(account)
    if available_balance < reserved_amount:
        api_key.status = "arrears"
        await db.flush()
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
        billing_source=billing_source,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(reservation)
    await db.flush()
    increment_metric("reservation.created_total")
    log_event(
        "reservation.created",
        user_id=user_id,
        api_key_id=api_key.id,
        request_id=request_id,
        model_code=model_code,
        reserved_amount=reserved_amount,
        status=reservation.status,
    )
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

    account = lock_wallet_account(reservation.user_id, db)
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "failed"
    reservation.error_message = error_message[:255]
    db.commit()
    db.refresh(reservation)
    increment_metric("reservation.failed_total")
    log_event(
        "reservation.released",
        user_id=reservation.user_id,
        api_key_id=reservation.api_key_id,
        request_id=reservation.request_id,
        reserved_amount=reservation.reserved_amount,
        status=reservation.status,
        reason=reservation.error_message,
    )
    return reservation


async def release_usage_reservation_async(
    *,
    request_id: str,
    error_message: str,
    db: AsyncSession,
    commit: bool = True,
) -> UsageReservation | None:
    reservation = (
        await db.execute(
            select(UsageReservation).where(UsageReservation.request_id == request_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not reservation or reservation.status != "pending":
        return reservation

    account = await lock_wallet_account_async(reservation.user_id, db)
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "failed"
    reservation.error_message = error_message[:255]
    await db.flush()
    increment_metric("reservation.failed_total")
    log_event(
        "reservation.released",
        user_id=reservation.user_id,
        api_key_id=reservation.api_key_id,
        request_id=reservation.request_id,
        reserved_amount=reservation.reserved_amount,
        status=reservation.status,
        reason=reservation.error_message,
    )
    if commit:
        await db.commit()
        await db.refresh(reservation)
    return reservation


def capture_usage_reservation(
    *,
    request_id: str,
    actual_amount: Decimal,
    description: str,
    reference_id: str,
    billing_source: str = "provider_usage",
    db: Session,
) -> tuple[UsageReservation, WalletAccount]:
    reservation = db.execute(
        select(UsageReservation).where(UsageReservation.request_id == request_id).with_for_update()
    ).scalar_one_or_none()
    if not reservation or reservation.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预占记录不存在")

    account = lock_wallet_account(reservation.user_id, db)

    if Decimal(account.balance) < actual_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算失败：余额不足")

    account.balance = Decimal(account.balance) - actual_amount
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "captured"
    reservation.actual_amount = actual_amount
    reservation.billing_source = billing_source

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
    increment_metric("reservation.captured_total")
    log_event(
        "reservation.captured",
        user_id=reservation.user_id,
        api_key_id=reservation.api_key_id,
        request_id=reservation.request_id,
        amount=actual_amount,
        reserved_amount=reservation.reserved_amount,
        status=reservation.status,
        reference_id=reference_id,
    )
    return reservation, account


async def capture_usage_reservation_async(
    *,
    request_id: str,
    actual_amount: Decimal,
    description: str,
    reference_id: str,
    billing_source: str = "provider_usage",
    db: AsyncSession,
    commit: bool = True,
) -> tuple[UsageReservation, WalletAccount]:
    reservation = (
        await db.execute(
            select(UsageReservation).where(UsageReservation.request_id == request_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not reservation or reservation.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预占记录不存在")

    account = await lock_wallet_account_async(reservation.user_id, db)
    if Decimal(account.balance) < actual_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结算失败：余额不足")

    account.balance = Decimal(account.balance) - actual_amount
    account.reserved_balance = max(
        Decimal("0.0000"),
        Decimal(account.reserved_balance) - Decimal(reservation.reserved_amount),
    )
    reservation.status = "captured"
    reservation.actual_amount = actual_amount
    reservation.billing_source = billing_source

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
    await db.flush()
    increment_metric("reservation.captured_total")
    log_event(
        "reservation.captured",
        user_id=reservation.user_id,
        api_key_id=reservation.api_key_id,
        request_id=reservation.request_id,
        amount=actual_amount,
        reserved_amount=reservation.reserved_amount,
        status=reservation.status,
        reference_id=reference_id,
    )
    if commit:
        await db.commit()
        await db.refresh(reservation)
        await db.refresh(account)
    return reservation, account


def mark_order_paid(order_no: str, db: Session, description: str = "充值到账") -> PaymentOrder:
    order = db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no).with_for_update()).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order.status == "paid":
        increment_metric("payment.idempotent_hits_total")
        log_event("payment.idempotent_hit", order_no=order_no, user_id=order.user_id, status=order.status)
        return order

    account = lock_wallet_account(order.user_id, db)
    _apply_locked_balance_change(
        account=account,
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
    try:
        db.commit()
        db.refresh(order)
        increment_metric("payment.recharge_success_total")
        log_event(
            "payment.mark_paid",
            order_no=order.order_no,
            user_id=order.user_id,
            amount=order.amount,
            status=order.status,
        )
        return order
    except IntegrityError:
        db.rollback()
        existing_order = db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no)).scalar_one()
        if existing_order.status == "paid":
            increment_metric("payment.idempotent_hits_total")
            log_event("payment.idempotent_hit", order_no=order_no, user_id=existing_order.user_id, status=existing_order.status)
            return existing_order
        raise


async def mark_order_paid_async(
    order_no: str,
    db: AsyncSession,
    *,
    description: str = "充值到账",
    channel_order_no: str | None = None,
) -> PaymentOrder:
    order = (
        await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no).with_for_update())
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if channel_order_no and order.channel_order_no != channel_order_no:
        order.channel_order_no = channel_order_no
    if order.status == "paid":
        increment_metric("payment.idempotent_hits_total")
        log_event("payment.idempotent_hit", order_no=order_no, user_id=order.user_id, status=order.status)
        await db.commit()
        await db.refresh(order)
        return order

    account = await lock_wallet_account_async(order.user_id, db)
    _apply_locked_balance_change(
        account=account,
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
    try:
        await db.commit()
        await db.refresh(order)
        increment_metric("payment.recharge_success_total")
        log_event(
            "payment.mark_paid",
            order_no=order.order_no,
            user_id=order.user_id,
            amount=order.amount,
            status=order.status,
        )
        return order
    except IntegrityError:
        await db.rollback()
        existing_order = (await db.execute(select(PaymentOrder).where(PaymentOrder.order_no == order_no))).scalar_one()
        if existing_order.status == "paid":
            increment_metric("payment.idempotent_hits_total")
            log_event("payment.idempotent_hit", order_no=order_no, user_id=existing_order.user_id, status=existing_order.status)
            return existing_order
        raise
