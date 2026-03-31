from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


def normalize_model_code(value: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "-").replace("/", "-")
    if not normalized:
        raise ValueError("平台模型编码不能为空")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if normalized[0] not in allowed or not normalized[0].isalnum():
        raise ValueError("平台模型编码需以小写字母或数字开头")
    if any(char not in allowed for char in normalized):
        raise ValueError("平台模型编码仅支持小写字母、数字、点、下划线和中划线")
    if len(normalized) < 2 or len(normalized) > 120:
        raise ValueError("平台模型编码长度需在 2 到 120 个字符之间")
    return normalized


class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    status: str
    balance: Decimal
    created_at: datetime


class AdjustBalanceRequest(BaseModel):
    amount: Decimal
    description: str = Field(min_length=2, max_length=255)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UpdateUserStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


class CreateModelRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=64)
    model_code: str
    model_id: str = Field(min_length=2, max_length=160)
    capability_type: str = Field(default="chat", min_length=2, max_length=32)
    billing_mode: str = Field(default="token", min_length=2, max_length=32)
    display_name: str = Field(min_length=2, max_length=120)
    vendor_display_name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=32)
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    rating: Decimal = Decimal("4.80")
    description: str = Field(default="", max_length=2000)
    hero_description: str = Field(default="", max_length=2000)
    support_features: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    pricing_items: list[dict[str, str]] = Field(default_factory=list)
    example_python: str = Field(default="", max_length=10000)
    example_typescript: str = Field(default="", max_length=10000)
    example_curl: str = Field(default="", max_length=10000)
    is_active: bool = True

    @field_validator("model_code", mode="before")
    @classmethod
    def validate_model_code(cls, value: str) -> str:
        return normalize_model_code(value)

    @field_validator("capability_type", mode="before")
    @classmethod
    def validate_capability_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        allowed = {"chat", "image", "embedding", "audio", "video"}
        if normalized not in allowed:
            raise ValueError("模型能力类型仅支持 chat、image、embedding、audio、video")
        return normalized

    @field_validator("billing_mode", mode="before")
    @classmethod
    def validate_billing_mode(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        allowed = {"token", "per_image", "per_second", "per_10k_chars"}
        if normalized not in allowed:
            raise ValueError("计费模式仅支持 token、per_image、per_second、per_10k_chars")
        return normalized

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: str) -> str:
        normalized_model_id = (value or "").strip()
        if not normalized_model_id:
            raise ValueError("真实模型 ID 不能为空")
        return normalized_model_id


class UpdateModelRequest(BaseModel):
    provider: str | None = Field(default=None, min_length=2, max_length=64)
    model_code: str | None = None
    model_id: str | None = Field(default=None, min_length=2, max_length=160)
    capability_type: str | None = Field(default=None, min_length=2, max_length=32)
    billing_mode: str | None = Field(default=None, min_length=2, max_length=32)
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    vendor_display_name: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=32)
    input_price_per_million: Decimal | None = None
    output_price_per_million: Decimal | None = None
    rating: Decimal | None = None
    description: str | None = Field(default=None, max_length=2000)
    hero_description: str | None = Field(default=None, max_length=2000)
    support_features: list[str] | None = None
    tags: list[str] | None = None
    pricing_items: list[dict[str, str]] | None = None
    example_python: str | None = Field(default=None, max_length=10000)
    example_typescript: str | None = Field(default=None, max_length=10000)
    example_curl: str | None = Field(default=None, max_length=10000)
    is_active: bool | None = None

    @field_validator("model_code", mode="before")
    @classmethod
    def validate_optional_model_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_model_code(value)

    @field_validator("capability_type", mode="before")
    @classmethod
    def validate_capability_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = (value or "").strip().lower()
        allowed = {"chat", "image", "embedding", "audio", "video"}
        if normalized not in allowed:
            raise ValueError("模型能力类型仅支持 chat、image、embedding、audio、video")
        return normalized

    @field_validator("billing_mode", mode="before")
    @classmethod
    def validate_optional_billing_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = (value or "").strip().lower()
        allowed = {"token", "per_image", "per_second", "per_10k_chars"}
        if normalized not in allowed:
            raise ValueError("计费模式仅支持 token、per_image、per_second、per_10k_chars")
        return normalized
