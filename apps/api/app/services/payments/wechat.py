from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from wechatpayv3 import WeChatPay, WeChatPayType

from app.core.config import settings
from app.services.payments.base import PaymentProvider, PaymentProviderResult
from app.services.payments.qr import build_qr_code_image


class WechatPayProvider(PaymentProvider):
    method = "wechat"

    def _client(self) -> WeChatPay:
        private_key = settings.read_text_if_exists(settings.wechat_private_key_path)
        if (
            not settings.wechat_app_id
            or not settings.wechat_mch_id
            or not settings.wechat_cert_serial_no
            or not settings.wechat_apiv3_key
            or not settings.wechat_notify_url
            or not private_key
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="微信支付未配置完成",
            )

        try:
            return WeChatPay(
                wechatpay_type=WeChatPayType.NATIVE,
                mchid=settings.wechat_mch_id,
                private_key=private_key,
                cert_serial_no=settings.wechat_cert_serial_no,
                appid=settings.wechat_app_id,
                apiv3_key=settings.wechat_apiv3_key,
                notify_url=settings.wechat_notify_url,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="微信支付配置无效，请检查商户私钥、证书序列号和 APIv3 Key",
            ) from exc

    def create_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> PaymentProviderResult:
        try:
            response = self._client().pay(
                description=subject,
                out_trade_no=order_no,
                amount={"total": int(amount * 100), "currency": "CNY"},
                pay_type=WeChatPayType.NATIVE,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="微信支付下单失败，请检查支付配置或网关连通性",
            ) from exc
        if not isinstance(response, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信支付下单失败")

        qr_code = response.get("code_url")
        return PaymentProviderResult(
            channel_order_no=response.get("out_trade_no", order_no),
            qr_code=qr_code,
            qr_code_image=build_qr_code_image(qr_code) if qr_code else None,
        )

    def query_payment(self, *, order_no: str, channel_order_no: str | None = None) -> dict:
        try:
            response = self._client().query(
                transaction_id=channel_order_no or None,
                out_trade_no=None if channel_order_no else order_no,
            )
        except Exception:  # noqa: BLE001
            return {"success": False, "status": "pending", "channel_order_no": channel_order_no}
        if not isinstance(response, dict):
            return {"success": False, "status": "pending", "channel_order_no": channel_order_no}
        return {
            "success": response.get("trade_state") == "SUCCESS",
            "status": str(response.get("trade_state", "pending")).lower(),
            "channel_order_no": response.get("transaction_id", channel_order_no),
        }

    def refund_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        refund_no: str,
        channel_order_no: str | None = None,
        reason: str | None = None,
    ) -> dict:
        try:
            response = self._client().refund(
                out_refund_no=refund_no,
                transaction_id=channel_order_no or None,
                out_trade_no=None if channel_order_no else order_no,
                amount={
                    "refund": int(amount * 100),
                    "total": int(amount * 100),
                    "currency": "CNY",
                },
                reason=reason or "申请退款",
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="微信退款失败，请检查支付配置或网关连通性",
            ) from exc
        if not isinstance(response, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信退款失败")
        return {
            "success": True,
            "channel_order_no": channel_order_no or response.get("transaction_id", ""),
            "channel_refund_no": response.get("refund_id", refund_no),
            "status": str(response.get("status", "success")).lower(),
            "raw": response,
        }

    def query_refund(
        self,
        *,
        order_no: str,
        refund_no: str,
        channel_order_no: str | None = None,
    ) -> dict:
        try:
            response = self._client().query_refund(out_refund_no=refund_no)
        except Exception:  # noqa: BLE001
            return {"success": False, "status": "unknown"}
        if not isinstance(response, dict):
            return {"success": False, "status": "unknown"}
        refund_status = str(response.get("status", "")).upper()
        return {
            "success": refund_status == "SUCCESS",
            "status": refund_status.lower() if refund_status else "unknown",
            "channel_order_no": channel_order_no or response.get("transaction_id", ""),
            "channel_refund_no": response.get("refund_id", refund_no),
            "raw": response,
        }

    def parse_notify(self, *, headers: dict[str, Any], body: Any) -> dict:
        raw_body = body.decode("utf-8") if isinstance(body, bytes) else str(body)
        try:
            result = self._client()._core.callback(headers=headers, body=raw_body)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信支付回调验签失败") from exc
        if not result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="微信支付回调验签失败")

        resource = result.get("resource") or {}
        return {
            "success": resource.get("trade_state") == "SUCCESS",
            "order_no": resource.get("out_trade_no", ""),
            "channel_order_no": resource.get("transaction_id", ""),
            "status": resource.get("trade_state", ""),
            "raw": result,
        }
