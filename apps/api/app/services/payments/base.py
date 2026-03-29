from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class PaymentProviderResult:
    channel_order_no: str | None = None
    payment_url: str | None = None
    qr_code: str | None = None
    qr_code_image: str | None = None


class PaymentProvider:
    method: str

    def create_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> PaymentProviderResult:
        raise NotImplementedError

    def query_payment(self, *, order_no: str, channel_order_no: str | None = None) -> dict:
        raise NotImplementedError

    def refund_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        refund_no: str,
        channel_order_no: str | None = None,
        reason: str | None = None,
    ) -> dict:
        raise NotImplementedError

    def query_refund(
        self,
        *,
        order_no: str,
        refund_no: str,
        channel_order_no: str | None = None,
    ) -> dict:
        raise NotImplementedError

    def parse_notify(self, *, headers: dict[str, Any], body: Any) -> dict:
        raise NotImplementedError

    def build_payment_page(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> str:
        raise NotImplementedError
