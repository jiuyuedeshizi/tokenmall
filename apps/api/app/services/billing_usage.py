from __future__ import annotations

from decimal import Decimal
import json


def resolve_billing_unit(billing_mode: str | None) -> str:
    normalized_mode = (billing_mode or "token").strip().lower()
    if normalized_mode == "per_image":
        return "image"
    if normalized_mode == "per_second":
        return "second"
    if normalized_mode == "per_10k_chars":
        return "char"
    return "token"


def infer_billing_quantity(
    *,
    total_tokens: int,
    billing_mode: str | None,
    billing_quantity: int | None = None,
    amount: Decimal | None = None,
    pricing_items: str | None = None,
) -> int:
    if billing_quantity and billing_quantity > 0:
        return billing_quantity
    if total_tokens > 0:
        return total_tokens

    normalized_mode = (billing_mode or "token").strip().lower()
    normalized_amount = Decimal(amount or "0")
    if normalized_amount <= Decimal("0"):
        return 0

    try:
        items = json.loads(pricing_items or "[]")
    except json.JSONDecodeError:
        items = []
    unit_price = Decimal("0")
    if items:
        try:
            unit_price = Decimal(str(items[0].get("price") or "0"))
        except Exception:  # noqa: BLE001
            unit_price = Decimal("0")

    if normalized_mode == "per_image":
        if unit_price > 0:
            return max(1, int((normalized_amount / unit_price).quantize(Decimal("1"))))
        return 1
    if normalized_mode == "per_second":
        if unit_price > 0:
            return max(1, int((normalized_amount / unit_price).quantize(Decimal("1"))))
        return 0
    if normalized_mode == "per_10k_chars":
        if unit_price > 0:
            return max(1, int(((normalized_amount / unit_price) * Decimal("10000")).quantize(Decimal("1"))))
        return 0
    return total_tokens
