import base64
import json
import logging
from decimal import Decimal
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from fastapi import HTTPException, status
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.request.AlipayTradePrecreateRequest import AlipayTradePrecreateRequest
from alipay.aop.api.request.AlipayTradeFastpayRefundQueryRequest import AlipayTradeFastpayRefundQueryRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest

from app.core.config import settings
from app.services.payments.base import PaymentProvider, PaymentProviderResult
from app.services.payments.qr import build_qr_code_image

logger = logging.getLogger(__name__)


class AlipayProvider(PaymentProvider):
    method = "alipay"

    def _is_processing_refund(self, response: dict[str, Any]) -> bool:
        return response.get("code", "") == "20000" and response.get("sub_code", "") == "aop.ACQ.SYSTEM_ERROR"

    def _normalize_response(self, response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            return response
        if isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="支付宝返回了无法解析的响应",
                ) from exc
        payload = getattr(response, "__dict__", None)
        if isinstance(payload, dict) and payload:
            return payload
        return {}

    def _public_key(self):
        public_key = settings.read_text_if_exists(settings.alipay_public_key_path)
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝公钥未配置",
            )
        try:
            return serialization.load_pem_public_key(public_key.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝公钥配置无效",
            ) from exc

    def _client(self) -> DefaultAlipayClient:
        private_key = settings.read_text_if_exists(settings.alipay_app_private_key_path)
        public_key = settings.read_text_if_exists(settings.alipay_public_key_path)
        if not settings.alipay_app_id or not private_key or not public_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝支付未配置完成",
            )

        try:
            config = AlipayClientConfig()
            config.server_url = settings.alipay_server_url
            config.app_id = settings.alipay_app_id
            config.app_private_key = private_key
            config.alipay_public_key = public_key
            return DefaultAlipayClient(config)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝支付配置无效，请检查应用密钥和公钥",
            ) from exc

    def create_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> PaymentProviderResult:
        request = AlipayTradePrecreateRequest()
        request.notify_url = settings.alipay_notify_url or None
        request.biz_content = {
            "out_trade_no": order_no,
            "total_amount": str(amount),
            "subject": subject,
        }
        try:
            response = self._normalize_response(self._client().execute(request))
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("支付宝下单请求异常")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝下单失败，请检查支付配置或网关连通性",
            ) from exc

        logger.info(
            "支付宝下单返回: code=%s msg=%s sub_code=%s sub_msg=%s out_trade_no=%s",
            response.get("code", ""),
            response.get("msg", ""),
            response.get("sub_code", ""),
            response.get("sub_msg", ""),
            response.get("out_trade_no", order_no),
        )
        if response.get("code", "") != "10000":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get("sub_msg") or response.get("msg") or "支付宝下单失败",
            )

        qr_code = response.get("qr_code")
        return PaymentProviderResult(
            channel_order_no=response.get("out_trade_no", order_no),
            qr_code=qr_code,
            qr_code_image=build_qr_code_image(qr_code) if qr_code else None,
        )

    def query_payment(self, *, order_no: str, channel_order_no: str | None = None) -> dict:
        request = AlipayTradeQueryRequest()
        request.biz_content = {
            "out_trade_no": order_no,
        }
        try:
            response = self._normalize_response(self._client().execute(request))
        except Exception:  # noqa: BLE001
            logger.exception("支付宝查询请求异常: out_trade_no=%s", order_no)
            return {"success": False, "status": "pending", "channel_order_no": channel_order_no}
        logger.info(
            "支付宝查询返回: code=%s msg=%s sub_code=%s sub_msg=%s out_trade_no=%s trade_no=%s trade_status=%s",
            response.get("code", ""),
            response.get("msg", ""),
            response.get("sub_code", ""),
            response.get("sub_msg", ""),
            order_no,
            response.get("trade_no", channel_order_no),
            response.get("trade_status", ""),
        )
        if response.get("code", "") != "10000":
            return {"success": False, "status": "pending", "channel_order_no": channel_order_no}
        return {
            "success": response.get("trade_status", "") == "TRADE_SUCCESS",
            "status": str(response.get("trade_status", "")).lower(),
            "channel_order_no": response.get("trade_no", channel_order_no),
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
        request = AlipayTradeRefundRequest()
        biz_content = {
            "out_trade_no": order_no,
            "refund_amount": str(amount),
            "out_request_no": refund_no,
            "refund_reason": reason or "申请退款",
        }
        if channel_order_no:
            biz_content["trade_no"] = channel_order_no
        request.biz_content = biz_content
        try:
            response = self._normalize_response(self._client().execute(request))
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("支付宝退款请求异常")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="支付宝退款失败，请检查支付配置或网关连通性",
            ) from exc

        logger.info(
            "支付宝退款返回: code=%s msg=%s sub_code=%s sub_msg=%s out_trade_no=%s trade_no=%s",
            response.get("code", ""),
            response.get("msg", ""),
            response.get("sub_code", ""),
            response.get("sub_msg", ""),
            order_no,
            response.get("trade_no", channel_order_no),
        )
        if self._is_processing_refund(response):
            return {
                "success": False,
                "channel_order_no": response.get("trade_no", channel_order_no),
                "channel_refund_no": refund_no,
                "status": "processing",
                "raw": response,
            }
        if response.get("code", "") != "10000":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get("sub_msg") or response.get("msg") or "支付宝退款失败",
            )

        return {
            "success": True,
            "channel_order_no": response.get("trade_no", channel_order_no),
            "channel_refund_no": refund_no,
            "status": "success",
            "raw": response,
        }

    def query_refund(
        self,
        *,
        order_no: str,
        refund_no: str,
        channel_order_no: str | None = None,
    ) -> dict:
        request = AlipayTradeFastpayRefundQueryRequest()
        biz_content = {
            "out_trade_no": order_no,
            "out_request_no": refund_no,
        }
        if channel_order_no:
            biz_content["trade_no"] = channel_order_no
        request.biz_content = biz_content
        try:
            response = self._normalize_response(self._client().execute(request))
        except Exception:  # noqa: BLE001
            logger.exception("支付宝退款查询请求异常: out_trade_no=%s out_request_no=%s", order_no, refund_no)
            return {"success": False, "status": "unknown"}
        refund_status = str(response.get("refund_status", "")).upper()
        if self._is_processing_refund(response):
            return {
                "success": False,
                "status": "processing",
                "channel_order_no": response.get("trade_no", channel_order_no),
                "channel_refund_no": response.get("out_request_no", refund_no),
                "raw": response,
            }
        return {
            "success": response.get("code", "") == "10000" and refund_status == "REFUND_SUCCESS",
            "status": refund_status.lower() if refund_status else "unknown",
            "channel_order_no": response.get("trade_no", channel_order_no),
            "channel_refund_no": response.get("out_request_no", refund_no),
            "raw": response,
        }

    def parse_notify(self, *, headers: dict[str, Any], body: Any) -> dict:
        payload = {key: str(value) for key, value in dict(body).items()}
        signature = payload.pop("sign", "")
        sign_type = payload.pop("sign_type", "RSA2")
        if not signature:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="支付宝回调缺少签名")

        sign_content = "&".join(
            f"{key}={value}"
            for key, value in sorted(payload.items())
            if value is not None and value != ""
        )

        algorithm = hashes.SHA256() if str(sign_type).upper() == "RSA2" else hashes.SHA1()
        try:
            self._public_key().verify(
                base64.b64decode(signature),
                sign_content.encode("utf-8"),
                padding.PKCS1v15(),
                algorithm,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="支付宝回调验签失败") from exc

        return {
            "success": payload.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"},
            "order_no": payload.get("out_trade_no", ""),
            "channel_order_no": payload.get("trade_no", ""),
            "status": payload.get("trade_status", ""),
            "raw": payload,
        }
