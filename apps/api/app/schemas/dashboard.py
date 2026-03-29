from decimal import Decimal

from pydantic import BaseModel


class DashboardActivity(BaseModel):
    time: str
    title: str
    subtitle: str
    tokens: int
    amount: Decimal


class DashboardPoint(BaseModel):
    label: str
    value: int


class DashboardSummary(BaseModel):
    total_requests: int
    month_spend: Decimal
    token_balance: Decimal
    success_rate: float
    recent_activities: list[DashboardActivity]
    monthly_usage: list[DashboardPoint]
    weekly_usage: list[DashboardPoint]
