from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CreatePaymentOrderRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: str


class PaymentOrderResponse(BaseModel):
    id: int
    order_no: str
    amount: Decimal
    payment_method: str
    channel_order_no: Optional[str] = None
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    qr_code_image: Optional[str] = None
    status: str
    paid_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateRefundRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class RefundSummaryResponse(BaseModel):
    refundable_amount: Decimal
    recharge_amount: Decimal
    consumed_amount: Decimal
    refunded_amount: Decimal
    pending_exists: bool


class RefundRequestResponse(BaseModel):
    id: int
    request_no: str
    amount: Decimal
    reason: str
    status: str
    admin_note: str
    reviewed_at: Optional[datetime]
    refunded_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
