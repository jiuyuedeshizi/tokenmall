from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select

from app.models import ApiKey, ModelCatalog, PaymentOrder, UsageLog, UsageReservation, User, WalletAccount, WalletLedger
from app.services.proxy import before_request_async, on_error_async
from app.services.reservation_cleanup import expire_usage_reservations
from app.services.wallet import mark_order_paid


def _seed_user(sync_session_factory):
    db = sync_session_factory()
    try:
        user = User(
            email="user@test.local",
            phone="13800000001",
            password_hash="hashed",
            name="Tester",
            role="user",
            status="active",
        )
        db.add(user)
        db.flush()
        db.add(WalletAccount(user_id=user.id, balance=Decimal("100.0000"), reserved_balance=Decimal("0.0000")))
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def _seed_api_key_and_model(sync_session_factory, user_id: int, *, request_limit: int | None = None) -> tuple[int, str]:
    db = sync_session_factory()
    try:
        api_key = ApiKey(
            user_id=user_id,
            name="Integration Key",
            key_prefix="tk_test",
            key_hash=f"hash_{user_id}_{request_limit or 0}",
            encrypted_key="enc",
            status="active",
            request_limit=request_limit,
            used_tokens=0,
            used_requests=0,
            used_amount=Decimal("0.0000"),
        )
        model = ModelCatalog(
            provider="alibaba-bailian",
            model_code=f"qwen-plus-{user_id}-{request_limit or 0}",
            model_id="qwen-plus",
            capability_type="chat",
            display_name="Qwen Plus",
            vendor_display_name="Qwen",
            category="text",
            billing_mode="token",
            pricing_items="[]",
            input_price_per_million=Decimal("1.0000"),
            output_price_per_million=Decimal("1.0000"),
            description="",
            hero_description="",
            support_features="",
            tags="",
            example_python="",
            example_typescript="",
            example_curl="",
            is_active=True,
        )
        db.add_all([api_key, model])
        db.commit()
        db.refresh(api_key)
        db.refresh(model)
        return api_key.id, model.model_code
    finally:
        db.close()


def test_concurrent_mark_order_paid_is_idempotent(sync_session_factory):
    user_id = _seed_user(sync_session_factory)
    db = sync_session_factory()
    try:
        order = PaymentOrder(
            order_no="ord_concurrency_1",
            user_id=user_id,
            amount=Decimal("25.00"),
            payment_method="mock",
            status="pending",
        )
        db.add(order)
        db.commit()
    finally:
        db.close()

    def worker():
        session = sync_session_factory()
        try:
            mark_order_paid("ord_concurrency_1", session, description="并发充值测试")
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker) for _ in range(10)]
        for future in futures:
            future.result()

    db = sync_session_factory()
    try:
        wallet = db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id)).scalar_one()
        order = db.execute(select(PaymentOrder).where(PaymentOrder.order_no == "ord_concurrency_1")).scalar_one()
        ledger_rows = db.execute(
            select(WalletLedger).where(
                WalletLedger.reference_type == "payment_order",
                WalletLedger.reference_id == "ord_concurrency_1",
            )
        ).scalars().all()
        assert order.status == "paid"
        assert Decimal(wallet.balance) == Decimal("125.0000")
        assert len(ledger_rows) == 1
    finally:
        db.close()


def test_async_api_key_limits_block_concurrent_reservations(async_session_factory, sync_session_factory):
    user_id = _seed_user(sync_session_factory)
    api_key_id, model_code = _seed_api_key_and_model(sync_session_factory, user_id, request_limit=1)

    async def attempt_call() -> str:
        async with async_session_factory() as db:
            api_key = (await db.execute(select(ApiKey).where(ApiKey.id == api_key_id))).scalar_one()
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
            model = (await db.execute(select(ModelCatalog).where(ModelCatalog.model_code == model_code))).scalar_one()
            return await before_request_async(
                api_key=api_key,
                user=user,
                payload={"messages": [{"role": "user", "content": "hello"}], "max_tokens": 64},
                model=model,
                db=db,
            )

    async def run_test():
        start_event = asyncio.Event()

        async def gated_attempt():
            await start_event.wait()
            return await attempt_call()

        tasks = [asyncio.create_task(gated_attempt()) for _ in range(2)]
        start_event.set()
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(run_test())
    successes = [item for item in results if isinstance(item, str)]
    failures = [item for item in results if isinstance(item, HTTPException)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 403

    db = sync_session_factory()
    try:
        reservations = db.execute(select(UsageReservation)).scalars().all()
        assert len(reservations) == 1
        assert reservations[0].status == "pending"
    finally:
        db.close()


def test_expire_usage_reservations_releases_reserved_balance(async_session_factory, sync_session_factory):
    user_id = _seed_user(sync_session_factory)
    api_key_id, model_code = _seed_api_key_and_model(sync_session_factory, user_id)

    db = sync_session_factory()
    try:
        wallet = db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id)).scalar_one()
        wallet.reserved_balance = Decimal("3.3000")
        db.add(
            UsageReservation(
                user_id=user_id,
                api_key_id=api_key_id,
                request_id="req_expired_1",
                model_code=model_code,
                reserved_amount=Decimal("3.3000"),
                estimated_input_tokens=100,
                estimated_output_tokens=50,
                billing_source="reserved_estimate",
                status="pending",
                error_message="",
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
        )
        db.commit()
    finally:
        db.close()

    async def run_cleanup():
        async with async_session_factory() as db:
            return await expire_usage_reservations(db)

    expired_count = asyncio.run(run_cleanup())
    assert expired_count == 1

    db = sync_session_factory()
    try:
        wallet = db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id)).scalar_one()
        reservation = db.execute(select(UsageReservation).where(UsageReservation.request_id == "req_expired_1")).scalar_one()
        assert Decimal(wallet.reserved_balance) == Decimal("0.0000")
        assert reservation.status == "expired"
    finally:
        db.close()


def test_on_error_async_releases_reservation_and_marks_arrears(async_session_factory, sync_session_factory):
    user_id = _seed_user(sync_session_factory)
    api_key_id, model_code = _seed_api_key_and_model(sync_session_factory, user_id)

    db = sync_session_factory()
    try:
        wallet = db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id)).scalar_one()
        wallet.reserved_balance = Decimal("2.0000")
        db.add(
            UsageReservation(
                user_id=user_id,
                api_key_id=api_key_id,
                request_id="req_error_1",
                model_code=model_code,
                reserved_amount=Decimal("2.0000"),
                estimated_input_tokens=10,
                estimated_output_tokens=10,
                billing_source="reserved_estimate",
                status="pending",
                error_message="",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        db.commit()
    finally:
        db.close()

    async def run_error():
        async with async_session_factory() as db:
            api_key = (await db.execute(select(ApiKey).where(ApiKey.id == api_key_id))).scalar_one()
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
            await on_error_async(
                api_key=api_key,
                user=user,
                request_id="req_error_1",
                model_code=model_code,
                error_message="余额不足",
                response_time_ms=12,
                db=db,
            )

    asyncio.run(run_error())

    db = sync_session_factory()
    try:
        wallet = db.execute(select(WalletAccount).where(WalletAccount.user_id == user_id)).scalar_one()
        reservation = db.execute(select(UsageReservation).where(UsageReservation.request_id == "req_error_1")).scalar_one()
        api_key = db.execute(select(ApiKey).where(ApiKey.id == api_key_id)).scalar_one()
        usage_logs = db.execute(select(UsageLog).where(UsageLog.request_id == "req_error_1")).scalars().all()
        assert Decimal(wallet.reserved_balance) == Decimal("0.0000")
        assert reservation.status == "failed"
        assert api_key.status == "arrears"
        assert len(usage_logs) == 1
    finally:
        db.close()
