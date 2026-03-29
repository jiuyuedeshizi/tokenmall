from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    token_limit: Optional[int] = Field(default=None, ge=1)
    request_limit: Optional[int] = Field(default=None, ge=1)
    budget_limit: Optional[Decimal] = Field(default=None, ge=0)


class UpdateApiKeyRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    token_limit: Optional[int] = Field(default=None, ge=1)
    request_limit: Optional[int] = Field(default=None, ge=1)
    budget_limit: Optional[Decimal] = Field(default=None, ge=0)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    status: str
    token_limit: Optional[int]
    request_limit: Optional[int]
    budget_limit: Optional[Decimal]
    used_tokens: int
    used_requests: int
    used_amount: Decimal
    last_used_at: Optional[datetime]
    created_at: datetime
    month_requests: int = 0
    success_rate: Decimal = Decimal("100.00")
    avg_response_time_ms: Optional[int] = None
    plaintext_key: Optional[str] = None

    model_config = {"from_attributes": True}
