from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ModelCatalog, PaymentOrder, UsageLog
from app.services.billing_usage import infer_billing_quantity, resolve_billing_unit

router = APIRouter()


def format_usage_quantity(quantity: int, billing_unit: str | None) -> str:
    normalized_unit = (billing_unit or "token").strip().lower()
    if normalized_unit == "image":
        return f"{quantity:,} 张"
    if normalized_unit == "second":
        return f"{quantity:,} 秒"
    if normalized_unit == "char":
        return f"{quantity:,} 字符"
    return f"{quantity:,} tokens"


def format_amount(amount: Decimal) -> str:
    normalized = f"{Decimal(amount):.6f}"
    integer, fraction = normalized.split(".")
    trimmed = fraction.rstrip("0")
    if len(trimmed) < 4:
        trimmed = fraction[:4]
    return f"{integer}.{trimmed}"


@router.get("/logs")
def list_usage_logs(
    keyword: str = Query(default=""),
    event_type: str = Query(default="all"),
    range_days: int | None = Query(default=7),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model_meta_map = {
        row.model_code: {
            "billing_mode": row.billing_mode,
            "pricing_items": row.pricing_items,
        }
        for row in db.query(ModelCatalog.model_code, ModelCatalog.billing_mode, ModelCatalog.pricing_items).all()
    }
    api_rows = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == current_user.id)
        .order_by(UsageLog.created_at.desc())
        .all()
    )
    paid_orders = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.user_id == current_user.id, PaymentOrder.status == "paid")
        .order_by(PaymentOrder.created_at.desc())
        .all()
    )

    items = [
        {
            "id": f"api-{row.id}",
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
            "billing_mode": model_meta_map.get(row.model_code, {}).get("billing_mode", "token"),
            "amount": row.amount,
            "status": row.status,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "event_type": "api",
            "title": f"{row.model_code} 的 API 请求已完成" if row.status == "success" else f"{row.model_code} 的 API 请求异常",
            "subtitle": (
                f"{row.model_code} · {format_usage_quantity(infer_billing_quantity(total_tokens=row.total_tokens, billing_mode=model_meta_map.get(row.model_code, {}).get('billing_mode', 'token'), billing_quantity=getattr(row, 'billing_quantity', 0), amount=Decimal(row.amount), pricing_items=model_meta_map.get(row.model_code, {}).get('pricing_items')), getattr(row, 'billing_unit', '') or resolve_billing_unit(model_meta_map.get(row.model_code, {}).get('billing_mode', 'token')))} · ¥{format_amount(row.amount)}"
                if row.status == "success"
                else f"{row.model_code} · - · -"
            ),
            "badge": "API",
        }
        for row in api_rows
    ]

    items.extend(
        [
            {
                "id": f"recharge-{order.id}",
                "model_code": "",
                "request_id": order.order_no,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": int(order.amount * 100),
                "billing_quantity": int(order.amount * 100),
                "billing_unit": "token",
                "billing_mode": "token",
                "amount": order.amount,
                "status": "success",
                "error_message": "",
                "created_at": order.created_at,
                "event_type": "token_recharge",
                "title": "Token 充值",
                "subtitle": f"{order.payment_method} · +{int(order.amount * 100):,} tokens · ¥{order.amount}",
                "badge": "Token 充值",
            }
            for order in paid_orders
        ]
    )

    if event_type != "all":
        items = [item for item in items if item["event_type"] == event_type]

    keyword = keyword.strip().lower()
    if keyword:
        items = [
            item
            for item in items
            if keyword in item["title"].lower()
            or keyword in item["subtitle"].lower()
            or keyword in item["request_id"].lower()
        ]

    if start_date and end_date:
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        items = [item for item in items if start_dt <= item["created_at"] <= end_dt]
    elif range_days:
        since = datetime.now(timezone.utc) - timedelta(days=range_days)
        items = [item for item in items if item["created_at"] >= since]

    items.sort(key=lambda item: item["created_at"], reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = items[start:end]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
