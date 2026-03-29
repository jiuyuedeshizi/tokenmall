from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PaymentOrder, RefundItem, RefundRequest, WalletAccount, WalletLedger
from app.schemas.payment import (
    CreatePaymentOrderRequest,
    CreateRefundRequest,
    PaymentOrderResponse,
    RefundRequestResponse,
    RefundSummaryResponse,
)
from app.services.payments import create_payment_provider
from app.services.wallet import create_payment_order, mark_order_paid, update_payment_order_channel

router = APIRouter()


def to_money_floor(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def _build_refund_summary(user_id: int, db: Session) -> dict:
    refundable_methods = ["alipay", "wechat", "unionpay"]
    recharge_amount = Decimal(
        db.query(func.coalesce(func.sum(PaymentOrder.amount), 0))
        .filter(
            PaymentOrder.user_id == user_id,
            PaymentOrder.status == "paid",
            PaymentOrder.payment_method.in_(refundable_methods),
        )
        .scalar()
        or 0
    )
    consumed_raw = Decimal(
        db.query(func.coalesce(func.sum(WalletLedger.amount), 0))
        .filter(WalletLedger.user_id == user_id, WalletLedger.type == "consume")
        .scalar()
        or 0
    )
    consumed_amount = abs(consumed_raw)
    refunded_amount = Decimal(
        db.query(func.coalesce(func.sum(RefundItem.amount), 0))
        .join(RefundRequest, RefundRequest.id == RefundItem.refund_request_id)
        .filter(
            RefundRequest.user_id == user_id,
            RefundRequest.status.in_(["pending", "processing", "approved", "refunded"]),
        )
        .scalar()
        or 0
    )
    wallet_balance = Decimal(
        db.query(func.coalesce(WalletAccount.balance, 0))
        .filter(WalletAccount.user_id == user_id)
        .scalar()
        or 0
    )
    pending_exists = (
        db.query(RefundRequest)
        .join(RefundItem, RefundItem.refund_request_id == RefundRequest.id)
        .filter(RefundRequest.user_id == user_id, RefundRequest.status == "pending")
        .first()
        is not None
    )
    remaining_recharge_amount = max(Decimal("0.00"), recharge_amount - refunded_amount)
    refundable_amount = max(Decimal("0.00"), min(wallet_balance, remaining_recharge_amount))
    consumed_amount = max(Decimal("0.00"), remaining_recharge_amount - refundable_amount)
    return {
        "refundable_amount": to_money_floor(refundable_amount),
        "recharge_amount": to_money_floor(recharge_amount),
        "consumed_amount": to_money_floor(consumed_amount),
        "refunded_amount": to_money_floor(refunded_amount),
        "pending_exists": pending_exists,
    }


def _build_refund_allocations(user_id: int, target_amount: Decimal, db: Session) -> list[tuple[PaymentOrder, Decimal]]:
    refundable_statuses = ["pending", "processing", "approved", "refunded"]
    orders = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.user_id == user_id,
            PaymentOrder.status == "paid",
            PaymentOrder.payment_method.in_(["alipay", "wechat", "unionpay"]),
        )
        .order_by(PaymentOrder.paid_at.desc().nullslast(), PaymentOrder.created_at.desc())
        .all()
    )
    candidates: list[tuple[PaymentOrder, Decimal]] = []
    for order in orders:
        already_refunded = Decimal(
            db.query(func.coalesce(func.sum(RefundItem.amount), 0))
            .join(RefundRequest, RefundRequest.id == RefundItem.refund_request_id)
            .filter(
                RefundItem.payment_order_id == order.id,
                RefundRequest.status.in_(refundable_statuses),
            )
            .scalar()
            or 0
        )
        available = max(Decimal("0.00"), Decimal(order.amount) - already_refunded)
        if available <= Decimal("0.00"):
            continue
        candidates.append((order, available))

    candidates.sort(
        key=lambda item: (
            item[1],
            item[0].paid_at or item[0].created_at,
            item[0].created_at,
        ),
        reverse=True,
    )

    allocations: list[tuple[PaymentOrder, Decimal]] = []
    remaining = Decimal(target_amount)
    for order, available in candidates:
        part = min(available, remaining)
        allocations.append((order, to_money_floor(part)))
        remaining -= part
        if remaining <= Decimal("0.00"):
            break
    if remaining > Decimal("0.00"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前可退款订单不足以覆盖退款金额")
    return allocations


@router.post("/orders", response_model=PaymentOrderResponse)
def create_order(
    payload: CreatePaymentOrderRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = create_payment_order(current_user, payload.amount, payload.payment_method, db)
    if payload.payment_method in {"alipay", "wechat", "unionpay"}:
        provider = create_payment_provider(payload.payment_method)
        result = provider.create_payment(
            order_no=order.order_no,
            amount=payload.amount,
            subject=f"TokenMall 余额充值 {payload.amount} 元",
        )
        return update_payment_order_channel(
            order,
            channel_order_no=result.channel_order_no,
            payment_url=result.payment_url,
            qr_code=result.qr_code,
            qr_code_image=result.qr_code_image,
            db=db,
        )
    return order


@router.post("/orders/{order_no}/mock-pay", response_model=PaymentOrderResponse)
def mock_pay_order(order_no: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no, PaymentOrder.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return mark_order_paid(order_no, db, description="模拟支付充值到账")


@router.get("/orders/{order_no}", response_model=PaymentOrderResponse)
def get_order(order_no: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no, PaymentOrder.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order.status == "pending" and order.payment_method in {"alipay", "wechat", "unionpay"}:
        provider = create_payment_provider(order.payment_method)
        result = provider.query_payment(order_no=order.order_no, channel_order_no=order.channel_order_no)
        if result.get("channel_order_no") and result.get("channel_order_no") != order.channel_order_no:
            order.channel_order_no = result["channel_order_no"]
            db.commit()
            db.refresh(order)
        if result.get("success"):
            desc_map = {
                "alipay": "支付宝充值到账",
                "wechat": "微信支付充值到账",
                "unionpay": "银联支付充值到账",
            }
            desc = desc_map.get(order.payment_method, "充值到账")
            return mark_order_paid(order.order_no, db, description=desc)
    return order


@router.get("/orders")
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.user_id == current_user.id)
        .order_by(PaymentOrder.created_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/refund-summary", response_model=RefundSummaryResponse)
def get_refund_summary(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _build_refund_summary(current_user.id, db)


@router.get("/refunds")
def list_refunds(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(RefundRequest)
        .filter(RefundRequest.user_id == current_user.id)
        .order_by(RefundRequest.created_at.desc())
    )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for row in rows:
        refunded_amount = Decimal(
            db.query(func.coalesce(func.sum(RefundItem.amount), 0))
            .filter(RefundItem.refund_request_id == row.id, RefundItem.status == "refunded")
            .scalar()
            or 0
        )
        amount = Decimal(row.amount)
        items.append(
            {
                "id": row.id,
                "request_no": row.request_no,
                "amount": row.amount,
                "reason": row.reason,
                "status": row.status,
                "admin_note": row.admin_note,
                "reviewed_at": row.reviewed_at,
                "refunded_at": row.refunded_at,
                "created_at": row.created_at,
                "refunded_amount": to_money_floor(refunded_amount),
                "remaining_amount": to_money_floor(max(Decimal("0.00"), amount - refunded_amount)),
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/refunds", response_model=RefundRequestResponse)
def create_refund(
    payload: CreateRefundRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = _build_refund_summary(current_user.id, db)
    if summary["pending_exists"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前已有一笔处理中退款申请")
    if summary["refundable_amount"] <= Decimal("0.00"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前无可申请退款金额")

    refund = RefundRequest(
        request_no=f"ref_{uuid4().hex[:18]}",
        user_id=current_user.id,
        amount=to_money_floor(summary["refundable_amount"]),
        reason=(payload.reason or "").strip(),
        status="pending",
    )
    db.add(refund)
    db.flush()
    for order, amount in _build_refund_allocations(current_user.id, summary["refundable_amount"], db):
        db.add(
            RefundItem(
                refund_request_id=refund.id,
                payment_order_id=order.id,
                payment_method=order.payment_method,
                amount=amount,
                status="pending",
            )
        )
    db.commit()
    db.refresh(refund)
    return refund


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    provider = create_payment_provider("alipay")
    result = provider.parse_notify(headers=dict(request.headers), body=await request.form())
    if result.get("success") and result.get("order_no"):
        order = db.query(PaymentOrder).filter(PaymentOrder.order_no == result["order_no"]).first()
        if order and result.get("channel_order_no") and order.channel_order_no != result["channel_order_no"]:
            order.channel_order_no = result["channel_order_no"]
            db.commit()
        mark_order_paid(result["order_no"], db, description="支付宝充值到账")
    return "success"


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    provider = create_payment_provider("wechat")
    result = provider.parse_notify(headers=dict(request.headers), body=body)
    if result.get("success") and result.get("order_no"):
        order = db.query(PaymentOrder).filter(PaymentOrder.order_no == result["order_no"]).first()
        if order and result.get("channel_order_no") and order.channel_order_no != result["channel_order_no"]:
            order.channel_order_no = result["channel_order_no"]
            db.commit()
        mark_order_paid(result["order_no"], db, description="微信支付充值到账")
    return {"code": "SUCCESS", "message": "成功"}


@router.get("/unionpay/pay/{order_no}", response_class=HTMLResponse)
def unionpay_pay_page(order_no: str, db: Session = Depends(get_db)):
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    if not order or order.payment_method != "unionpay":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="银联支付订单不存在")
    provider = create_payment_provider("unionpay")
    return provider.build_payment_page(
        order_no=order.order_no,
        amount=Decimal(order.amount),
        subject=f"TokenMall 余额充值 {order.amount} 元",
    )


@router.post("/unionpay/notify")
async def unionpay_notify(request: Request, db: Session = Depends(get_db)):
    provider = create_payment_provider("unionpay")
    result = provider.parse_notify(headers=dict(request.headers), body=await request.form())
    if result.get("success") and result.get("order_no"):
        order = db.query(PaymentOrder).filter(PaymentOrder.order_no == result["order_no"]).first()
        if order and result.get("channel_order_no") and order.channel_order_no != result["channel_order_no"]:
            order.channel_order_no = result["channel_order_no"]
            db.commit()
        mark_order_paid(result["order_no"], db, description="银联支付充值到账")
    return "ok"
