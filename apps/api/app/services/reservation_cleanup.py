import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import UsageReservation, WalletAccount
from app.services.observability import increment_metric, log_event

logger = logging.getLogger(__name__)

RESERVATION_CLEANUP_INTERVAL_SECONDS = 60


async def expire_usage_reservations(db: AsyncSession) -> int:
    expired_reservations = (
        await db.execute(
            select(UsageReservation)
            .where(
                UsageReservation.status == "pending",
                UsageReservation.expires_at < datetime.now(timezone.utc),
            )
            .with_for_update(skip_locked=True)
        )
    ).scalars().all()
    if not expired_reservations:
        return 0

    wallet_ids = {reservation.user_id for reservation in expired_reservations}
    locked_wallets = (
        await db.execute(
            select(WalletAccount).where(WalletAccount.user_id.in_(wallet_ids)).with_for_update()
        )
    ).scalars().all()
    wallet_by_user_id = {wallet.user_id: wallet for wallet in locked_wallets}

    expired_count = 0
    for reservation in expired_reservations:
        wallet = wallet_by_user_id.get(reservation.user_id)
        if wallet is not None:
            wallet.reserved_balance = max(
                Decimal("0.0000"),
                Decimal(wallet.reserved_balance) - Decimal(reservation.reserved_amount),
            )
        reservation.status = "expired"
        reservation.error_message = "预占超时已自动释放"
        increment_metric("reservation.expired_total")
        log_event(
            "reservation.expired",
            user_id=reservation.user_id,
            api_key_id=reservation.api_key_id,
            request_id=reservation.request_id,
            reserved_amount=reservation.reserved_amount,
            status=reservation.status,
        )
        expired_count += 1

    await db.commit()
    return expired_count


async def run_reservation_cleanup_once() -> int:
    async with AsyncSessionLocal() as db:
        return await expire_usage_reservations(db)


async def execute_reservation_cleanup(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            expired_count = await run_reservation_cleanup_once()
            if expired_count:
                logger.info("Released %s expired usage reservations", expired_count)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to release expired usage reservations")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RESERVATION_CLEANUP_INTERVAL_SECONDS)
        except TimeoutError:
            continue


async def reservation_cleanup_loop(stop_event: asyncio.Event) -> None:
    await execute_reservation_cleanup(stop_event)
