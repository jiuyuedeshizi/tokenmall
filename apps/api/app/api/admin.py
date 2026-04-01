from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models import ApiKey, ModelCatalog, PaymentOrder, RefundItem, RefundRequest, UsageLog, User, WalletAccount, WalletLedger
from app.schemas.admin import AdjustBalanceRequest, AdminResetPasswordRequest, CreateModelRequest, UpdateModelRequest
from app.services.api_keys import delete_api_key as delete_api_key_service
from app.services.auth import admin_reset_password
from app.services.billing_usage import infer_billing_quantity, resolve_billing_unit
from app.services.official_model_catalog import get_official_model_examples
from app.services.payments import create_payment_provider
from app.services.wallet import apply_balance_change, mark_order_paid

router = APIRouter()
MULTIMODAL_CHAT_MODELS = {"qwen-plus", "qwen-flash", "kimi-k2.5", "qwen3-asr-flash"}


def parse_pricing_items(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def ensure_model_pricing_items(model: ModelCatalog) -> list[dict]:
    items = parse_pricing_items(model.pricing_items)
    if items:
        return items
    return [
        {"label": "输入", "unit": "元/百万Token", "price": str(model.input_price_per_million)},
        {"label": "输出", "unit": "元/百万Token", "price": str(model.output_price_per_million)},
    ]


def build_default_pricing_items(input_price: Decimal, output_price: Decimal, billing_mode: str = "token") -> str:
    if billing_mode == "per_image":
        items = [{"label": "图片生成", "unit": "元/张", "price": str(output_price.normalize())}]
    elif billing_mode == "per_second":
        items = [{"label": "语音/视频生成", "unit": "元/每秒", "price": str(output_price.normalize())}]
    elif billing_mode == "per_10k_chars":
        items = [{"label": "文本处理", "unit": "元/每万字符", "price": str(output_price.normalize())}]
    else:
        items = [
            {"label": "输入", "unit": "元/百万Token", "price": str(input_price.normalize())},
            {"label": "输出", "unit": "元/百万Token", "price": str(output_price.normalize())},
        ]
    return json.dumps(items, ensure_ascii=False)


def serialize_model(model: ModelCatalog):
    examples = get_official_model_examples(model.model_code)
    supports_multimodal_chat = (
        model.capability_type == "chat"
        and (model.model_code or "").strip().lower() in MULTIMODAL_CHAT_MODELS
    )
    return {
        "id": model.id,
        "provider": model.provider,
        "supports_multimodal_chat": supports_multimodal_chat,
        "model_code": model.model_code,
        "model_id": model.model_id,
        "capability_type": model.capability_type,
        "display_name": model.display_name,
        "vendor_display_name": model.vendor_display_name,
        "category": model.category,
        "billing_mode": model.billing_mode,
        "pricing_items": ensure_model_pricing_items(model),
        "input_price_per_million": model.input_price_per_million,
        "output_price_per_million": model.output_price_per_million,
        "rating": model.rating,
        "description": model.description,
        "hero_description": model.hero_description,
        "support_features": [item.strip() for item in model.support_features.split(",") if item.strip()],
        "tags": [item.strip() for item in model.tags.split(",") if item.strip()],
        "example_python": model.example_python or examples.get("example_python", ""),
        "example_typescript": model.example_typescript or examples.get("example_typescript", ""),
        "example_curl": model.example_curl or examples.get("example_curl", ""),
        "is_active": model.is_active,
        "created_at": model.created_at,
    }

@router.get("/overview")
def get_admin_overview(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    recent_orders = db.query(PaymentOrder).order_by(PaymentOrder.created_at.desc()).limit(5).all()
    recent_errors = (
        db.query(UsageLog)
        .filter(UsageLog.status != "success")
        .order_by(UsageLog.created_at.desc())
        .limit(5)
        .all()
    )
    total_requests = db.query(UsageLog).count()
    success_requests = db.query(UsageLog).filter(UsageLog.status == "success").count()
    month_spend = (
        db.query(UsageLog)
        .filter(UsageLog.created_at >= month_start)
        .with_entities(UsageLog.amount)
        .all()
    )
    total_spend = sum((Decimal(item[0]) for item in month_spend), Decimal("0.0000"))
    return {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.status == "active").count(),
        "total_api_keys": db.query(ApiKey).count(),
        "active_models": db.query(ModelCatalog).filter(ModelCatalog.is_active.is_(True)).count(),
        "total_requests": total_requests,
        "success_rate": round((success_requests / total_requests) * 100, 2) if total_requests else 100,
        "month_spend": total_spend,
        "pending_orders": db.query(PaymentOrder).filter(PaymentOrder.status == "pending").count(),
        "recent_orders": [
            {
                "order_no": item.order_no,
                "amount": item.amount,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in recent_orders
        ],
        "recent_errors": [
            {
                "request_id": item.request_id,
                "model_code": item.model_code,
                "error_message": item.error_message,
                "created_at": item.created_at,
            }
            for item in recent_errors
        ],
    }


@router.get("/users")
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(User, WalletAccount)
        .join(WalletAccount, WalletAccount.user_id == User.id)
        .order_by(User.created_at.desc())
    )
    total = db.query(User).count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "status": user.status,
            "balance": wallet.balance,
            "reserved_balance": wallet.reserved_balance,
            "api_key_count": db.query(ApiKey).filter(ApiKey.user_id == user.id).count(),
            "created_at": user.created_at,
        }
        for user, wallet in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/users/{user_id}")
def get_user_detail(user_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    wallet = db.query(WalletAccount).filter(WalletAccount.user_id == user.id).first()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "status": user.status,
        "balance": wallet.balance if wallet else Decimal("0"),
        "reserved_balance": wallet.reserved_balance if wallet else Decimal("0"),
        "api_key_count": db.query(ApiKey).filter(ApiKey.user_id == user.id).count(),
        "created_at": user.created_at,
    }


@router.post("/users/{user_id}/enable")
def enable_user(user_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.status = "active"
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/disable")
def disable_user(user_id: int, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能禁用当前管理员账号")
    if user.role == "admin":
        active_admin_count = db.query(User).filter(User.role == "admin", User.status == "active").count()
        if user.status == "active" and active_admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少保留一个可用管理员账号")
    user.status = "disabled"
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/adjust-balance")
def adjust_user_balance(
    user_id: int,
    payload: AdjustBalanceRequest,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    account = apply_balance_change(
        user_id=user_id,
        amount=payload.amount,
        ledger_type="adjust",
        reference_type="admin_adjust",
        reference_id=f"user-{user_id}",
        description=payload.description,
        db=db,
    )
    db.commit()
    return {"balance": account.balance}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    admin_reset_password(user, payload.new_password, db)
    return {"success": True}


@router.get("/orders")
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(PaymentOrder).order_by(PaymentOrder.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user for user in db.query(User).all()}
    items = [
        {
            "id": row.id,
            "order_no": row.order_no,
            "user_id": row.user_id,
            "user_email": users.get(row.user_id).email if users.get(row.user_id) else "",
            "user_name": users.get(row.user_id).name if users.get(row.user_id) else "",
            "amount": row.amount,
            "payment_method": row.payment_method,
            "status": row.status,
            "paid_at": row.paid_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/orders/{order_no}/mark-paid")
def admin_mark_paid(order_no: str, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return mark_order_paid(order_no, db, description="管理员手工充值到账")


@router.get("/refunds")
def list_refunds(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(RefundRequest).order_by(RefundRequest.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user for user in db.query(User).all()}
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
                "user_id": row.user_id,
                "user_email": users.get(row.user_id).email if users.get(row.user_id) else "",
                "user_name": users.get(row.user_id).name if users.get(row.user_id) else "",
                "amount": row.amount,
                "reason": row.reason,
                "status": row.status,
                "admin_note": row.admin_note,
                "reviewed_at": row.reviewed_at,
                "refunded_at": row.refunded_at,
                "created_at": row.created_at,
                "refunded_amount": refunded_amount,
                "remaining_amount": max(Decimal("0.00"), amount - refunded_amount),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/refunds/{refund_id}/approve")
def approve_refund(refund_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退款申请不存在")
    if refund.status not in {"pending", "processing"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前退款申请状态不可处理")
    refund_items = (
        db.query(RefundItem)
        .filter(RefundItem.refund_request_id == refund.id)
        .order_by(RefundItem.id.asc())
        .all()
    )
    if not refund_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="退款申请缺少可退款订单")
    remaining_amount = sum(
        (Decimal(item.amount) for item in refund_items if item.status != "refunded"),
        Decimal("0.00"),
    )
    wallet = db.query(WalletAccount).filter(WalletAccount.user_id == refund.user_id).first()
    if not wallet or Decimal(wallet.balance) < remaining_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前用户余额不足，无法原路退款")

    processed_at = datetime.now(timezone.utc)
    refunded_total = Decimal("0.00")
    try:
        for item in refund_items:
            if item.status == "refunded":
                refunded_total += Decimal(item.amount)
                continue
            if item.status == "processing":
                refund.reviewed_at = processed_at
                refund.status = "processing"
                refund.admin_note = "退款处理中，请稍后查询渠道结果"
                continue

            order = db.query(PaymentOrder).filter(PaymentOrder.id == item.payment_order_id).first()
            if not order:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="退款关联订单不存在")
            if order.payment_method not in {"alipay", "wechat", "unionpay"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持支付宝、微信和银联原路退款")

            provider = create_payment_provider(order.payment_method)
            refund_no = f"{refund.request_no}_{item.id}"
            result = provider.query_refund(
                order_no=order.order_no,
                channel_order_no=order.channel_order_no,
                refund_no=refund_no,
            )
            if result.get("status") == "processing":
                item.status = "processing"
                item.channel_refund_no = result.get("channel_refund_no", refund_no) or refund_no
                refund.reviewed_at = processed_at
                refund.status = "processing"
                refund.admin_note = "退款处理中，请稍后查询渠道结果"
                db.commit()
                continue
            if not result.get("success"):
                try:
                    result = provider.refund_payment(
                        order_no=order.order_no,
                        channel_order_no=order.channel_order_no,
                        amount=Decimal(item.amount),
                        refund_no=refund_no,
                        reason=refund.reason or "申请退款",
                    )
                    if result.get("status") == "processing":
                        item.status = "processing"
                        item.channel_refund_no = result.get("channel_refund_no", refund_no) or refund_no
                        refund.reviewed_at = processed_at
                        refund.status = "processing"
                        refund.admin_note = "退款处理中，请稍后查询渠道结果"
                        db.commit()
                        continue
                except HTTPException:
                    retry_result = provider.query_refund(
                        order_no=order.order_no,
                        channel_order_no=order.channel_order_no,
                        refund_no=refund_no,
                    )
                    if retry_result.get("status") == "processing":
                        item.status = "processing"
                        item.channel_refund_no = retry_result.get("channel_refund_no", refund_no) or refund_no
                        refund.reviewed_at = processed_at
                        refund.status = "processing"
                        refund.admin_note = "退款处理中，请稍后查询渠道结果"
                        db.commit()
                        continue
                    if not retry_result.get("success"):
                        raise
                    result = retry_result
            if not result.get("success"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="退款渠道处理失败")

            apply_balance_change(
                user_id=refund.user_id,
                amount=-Decimal(item.amount),
                ledger_type="refund",
                reference_type="refund_request",
                reference_id=f"{refund.request_no}:{item.id}",
                description=f"{'支付宝' if order.payment_method == 'alipay' else '微信支付' if order.payment_method == 'wechat' else '银联支付'}原路退款",
                db=db,
            )
            item.status = "refunded"
            item.channel_refund_no = result.get("channel_refund_no", refund_no) or refund_no
            refunded_total += Decimal(item.amount)
            refund.reviewed_at = processed_at
            refund.status = "processing"
            refund.admin_note = "退款处理中"
            db.commit()
            db.refresh(refund)
    except HTTPException as exc:
        refund.reviewed_at = processed_at
        refund.status = "processing" if refunded_total > Decimal("0.00") else "pending"
        refund.admin_note = exc.detail if isinstance(exc.detail, str) else "退款处理失败"
        db.commit()
        raise

    refund.reviewed_at = processed_at
    refund.refunded_at = processed_at
    refund.status = "refunded" if refunded_total >= Decimal(refund.amount) else "processing"
    refund.admin_note = "已原路退款" if refund.status == "refunded" else "部分退款已完成，请继续处理"
    db.commit()
    db.refresh(refund)
    return {
        "success": True,
        "status": refund.status,
        "message": "已完成原路退款" if refund.status == "refunded" else "部分退款已完成，剩余退款正在渠道处理中",
    }


@router.post("/refunds/{refund_id}/reject")
def reject_refund(refund_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="退款申请不存在")
    if refund.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前退款申请状态不可处理")
    refund.status = "rejected"
    refund.reviewed_at = datetime.now(timezone.utc)
    if not refund.admin_note:
        refund.admin_note = "不符合退款条件"
    db.commit()
    return {"success": True}


@router.get("/api-keys")
def admin_list_api_keys(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(ApiKey).order_by(ApiKey.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user for user in db.query(User).all()}
    items = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "user_email": users.get(row.user_id).email if users.get(row.user_id) else "",
            "user_name": users.get(row.user_id).name if users.get(row.user_id) else "",
            "name": row.name,
            "key_prefix": row.key_prefix,
            "status": row.status,
            "token_limit": row.token_limit,
            "request_limit": row.request_limit,
            "budget_limit": row.budget_limit,
            "used_tokens": row.used_tokens,
            "used_requests": row.used_requests,
            "used_amount": row.used_amount,
            "last_used_at": row.last_used_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/api-keys/{key_id}/enable")
def admin_enable_api_key(key_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    api_key.status = "active"
    db.commit()
    return {"success": True}


@router.post("/api-keys/{key_id}/disable")
def admin_disable_api_key(key_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    api_key.status = "disabled"
    db.commit()
    return {"success": True}


@router.delete("/api-keys/{key_id}")
def admin_delete_api_key(key_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    delete_api_key_service(api_key, db)
    return {"success": True}


@router.get("/ledger")
def list_wallet_ledger(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(WalletLedger).order_by(WalletLedger.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user for user in db.query(User).all()}
    items = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "user_email": users.get(row.user_id).email if users.get(row.user_id) else "",
            "user_name": users.get(row.user_id).name if users.get(row.user_id) else "",
            "type": row.type,
            "amount": row.amount,
            "balance_after": row.balance_after,
            "reference_type": row.reference_type,
            "reference_id": row.reference_id,
            "description": row.description,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/usage")
def list_usage_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(UsageLog).order_by(UsageLog.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    users = {user.id: user for user in db.query(User).all()}
    model_meta_map = {
        row.model_code: {
            "billing_mode": row.billing_mode,
            "pricing_items": row.pricing_items,
        }
        for row in db.query(ModelCatalog.model_code, ModelCatalog.billing_mode, ModelCatalog.pricing_items).all()
    }
    items = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "user_email": users.get(row.user_id).email if users.get(row.user_id) else "",
            "user_name": users.get(row.user_id).name if users.get(row.user_id) else "",
            "api_key_id": row.api_key_id,
            "model_code": row.model_code,
            "request_id": row.request_id,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens,
            "billing_quantity": infer_billing_quantity(
                total_tokens=row.total_tokens,
                billing_mode=model_meta_map.get(row.model_code, {}).get("billing_mode", "token"),
                billing_quantity=getattr(row, "billing_quantity", 0),
                amount=Decimal(row.amount),
                pricing_items=model_meta_map.get(row.model_code, {}).get("pricing_items"),
            ),
            "billing_unit": getattr(row, "billing_unit", "") or resolve_billing_unit(model_meta_map.get(row.model_code, {}).get("billing_mode", "token")),
            "amount": row.amount,
            "billing_source": row.billing_source,
            "status": row.status,
            "error_message": row.error_message,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/models")
def list_models(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(ModelCatalog).order_by(ModelCatalog.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [serialize_model(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/models")
def create_model(payload: CreateModelRequest, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    existing = db.query(ModelCatalog).filter(ModelCatalog.model_code == payload.model_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型编码已存在")
    if payload.model_code != payload.model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="透明代理要求 model_id 与 model_code 完全一致")
    model = ModelCatalog(
        provider=payload.provider,
        model_code=payload.model_code,
        model_id=payload.model_id,
        capability_type=payload.capability_type,
        display_name=payload.display_name,
        vendor_display_name=payload.vendor_display_name,
        category=payload.category,
        billing_mode=payload.billing_mode,
        pricing_items=json.dumps(payload.pricing_items, ensure_ascii=False) if payload.pricing_items else build_default_pricing_items(payload.input_price_per_million, payload.output_price_per_million, payload.billing_mode),
        input_price_per_million=payload.input_price_per_million,
        output_price_per_million=payload.output_price_per_million,
        rating=payload.rating,
        description=payload.description,
        hero_description=payload.hero_description,
        support_features=",".join(payload.support_features),
        tags=",".join(payload.tags),
        example_python=payload.example_python,
        example_typescript=payload.example_typescript,
        example_curl=payload.example_curl,
        is_active=payload.is_active,
    )
    db.add(model)
    db.flush()
    db.commit()
    db.refresh(model)
    return serialize_model(model)


@router.patch("/models/{model_id}")
def update_model(
    model_id: int,
    payload: UpdateModelRequest,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    model = db.query(ModelCatalog).filter(ModelCatalog.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    update_data = payload.model_dump(exclude_unset=True)
    if "model_code" in update_data:
        duplicate = (
            db.query(ModelCatalog)
            .filter(ModelCatalog.model_code == update_data["model_code"], ModelCatalog.id != model.id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型编码已存在")
    for key, value in update_data.items():
        if key in {"support_features", "tags"} and value is not None:
            setattr(model, key, ",".join(value))
        elif key == "pricing_items" and value is not None:
            setattr(model, key, json.dumps(value, ensure_ascii=False))
        else:
            setattr(model, key, value)
    if model.model_code != model.model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="透明代理要求 model_id 与 model_code 完全一致")
    if not model.pricing_items:
        model.pricing_items = build_default_pricing_items(
            Decimal(model.input_price_per_million),
            Decimal(model.output_price_per_million),
            model.billing_mode,
        )
    db.commit()
    db.refresh(model)
    return serialize_model(model)


@router.post("/models/{model_id}/enable")
def enable_model(model_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    model = db.query(ModelCatalog).filter(ModelCatalog.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    model.is_active = True
    db.commit()
    return {"success": True}


@router.post("/models/{model_id}/disable")
def disable_model(model_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    model = db.query(ModelCatalog).filter(ModelCatalog.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    model.is_active = False
    db.commit()
    return {"success": True}


@router.delete("/models/{model_id}")
def delete_model(model_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    model = db.query(ModelCatalog).filter(ModelCatalog.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    db.delete(model)
    db.commit()
    return {"success": True}
