from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class WalletResponse(BaseModel):
    balance: Decimal
    reserved_balance: Decimal
    available_balance: Decimal
    currency: str


class WalletLedgerResponse(BaseModel):
    id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    description: str
    reference_type: str
    reference_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
