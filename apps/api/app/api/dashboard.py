from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PaymentOrder, UsageLog, WalletAccount
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def get_summary(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    usages = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == current_user.id)
        .order_by(UsageLog.created_at.desc())
        .all()
    )
    paid_orders = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.user_id == current_user.id, PaymentOrder.status == "paid")
        .order_by(PaymentOrder.paid_at.desc(), PaymentOrder.created_at.desc())
        .all()
    )
    wallet = db.query(WalletAccount).filter(WalletAccount.user_id == current_user.id).first()
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_spend = sum(
        (Decimal(item.amount) for item in usages if item.created_at >= start_of_month),
        start=Decimal("0.0000"),
    )
    total_requests = len([item for item in usages if item.status == "success"])
    success_count = total_requests
    success_rate = 0.0 if not usages else round(success_count / len(usages) * 100, 1)

    recent_activities = [
        {
            "sort_time": item.created_at,
            "time": item.created_at.strftime("%H:%M"),
            "title": "API调用" if item.status == "success" else "调用失败",
            "subtitle": item.model_code,
            "tokens": item.total_tokens,
            "amount": item.amount,
        }
        for item in usages[:6]
    ] + [
        {
            "sort_time": item.paid_at or item.created_at,
            "time": (item.paid_at or item.created_at).strftime("%H:%M"),
            "title": "余额充值",
            "subtitle": item.payment_method,
            "tokens": 0,
            "amount": item.amount,
        }
        for item in paid_orders[:6]
    ]
    recent_activities = [
        {
            "time": item["time"],
            "title": item["title"],
            "subtitle": item["subtitle"],
            "tokens": item["tokens"],
            "amount": item["amount"],
        }
        for item in sorted(recent_activities, key=lambda entry: entry["sort_time"], reverse=True)[:6]
    ]

    monthly_map: dict[str, int] = defaultdict(int)
    for item in usages:
        label = f"{item.created_at.month}月"
        monthly_map[label] += item.total_tokens

    monthly_usage = []
    for months_ago in range(5, -1, -1):
        anchor = now.replace(day=15) - timedelta(days=months_ago * 30)
        label = f"{anchor.month}月"
        monthly_usage.append({"label": label, "value": monthly_map.get(label, 0)})

    weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    start_of_week = (now - timedelta(days=now.weekday())).date()
    weekly_usage = []
    for offset in range(7):
        day = start_of_week + timedelta(days=offset)
        total = sum(item.total_tokens for item in usages if item.created_at.date() == day)
        weekly_usage.append({"label": weekday_labels[offset], "value": total})

    return DashboardSummary(
        total_requests=total_requests,
        month_spend=month_spend.quantize(Decimal("0.0001")),
        token_balance=Decimal(wallet.balance if wallet else 0),
        success_rate=success_rate,
        recent_activities=recent_activities,
        monthly_usage=monthly_usage,
        weekly_usage=weekly_usage,
    )
