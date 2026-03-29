from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from html import escape
from typing import Any
from urllib.parse import quote_plus

import base64
import hashlib

import httpx
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.payments.base import PaymentProvider, PaymentProviderResult


def _fen(amount: Decimal) -> str:
    return str(int((Decimal(amount) * Decimal("100")).quantize(Decimal("1"))))


class UnionPayProvider(PaymentProvider):
    method = "unionpay"

    def _normalize_id(self, value: str, *, prefix: str) -> str:
        normalized = "".join(char for char in value if char.isalnum())
        if not normalized:
            normalized = prefix
        return normalized[:40]

    def _load_signing_material(self) -> tuple[Any, x509.Certificate]:
        cert_bytes = self._read_binary(settings.unionpay_sign_cert_path)
        if not cert_bytes or not settings.unionpay_sign_cert_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="银联支付未配置完成",
            )
        try:
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                cert_bytes,
                settings.unionpay_sign_cert_password.encode("utf-8"),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="银联签名证书配置无效",
            ) from exc
        if private_key is None or certificate is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="银联签名证书配置无效",
            )
        return private_key, certificate

    def _load_certificate(self, file_path: str, error_detail: str) -> x509.Certificate | None:
        cert_bytes = self._read_binary(file_path)
        if not cert_bytes:
            return None
        try:
            if b"BEGIN CERTIFICATE" in cert_bytes:
                return x509.load_pem_x509_certificate(cert_bytes)
            return x509.load_der_x509_certificate(cert_bytes)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail,
            ) from exc

    def _load_verify_chain(self) -> tuple[x509.Certificate | None, x509.Certificate | None]:
        root_cert = self._load_certificate(settings.unionpay_root_cert_path, "银联根证书配置无效")
        middle_cert = self._load_certificate(settings.unionpay_middle_cert_path, "银联中级证书配置无效")
        return root_cert, middle_cert

    def _match_cert_by_cert_id(self, cert_id: str | None) -> x509.Certificate | None:
        root_cert, middle_cert = self._load_verify_chain()
        candidates = [middle_cert, root_cert]
        if cert_id:
            for cert in candidates:
                if cert and str(cert.serial_number) == str(cert_id):
                    return cert
        for cert in candidates:
            if cert:
                return cert
        return None

    def _issuer_matches(self, child: x509.Certificate, issuer: x509.Certificate) -> bool:
        return child.issuer == issuer.subject

    def _is_trusted_by_chain(self, cert: x509.Certificate) -> bool:
        root_cert, middle_cert = self._load_verify_chain()
        if middle_cert and root_cert:
            return self._issuer_matches(cert, middle_cert) and self._issuer_matches(middle_cert, root_cert)
        if middle_cert:
            return self._issuer_matches(cert, middle_cert)
        if root_cert:
            return self._issuer_matches(cert, root_cert)
        return True

    def _digest_text(self, payload: str, algorithm: str = "sha1") -> str:
        if algorithm.lower() == "sha256":
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def signing_certificate_summary(self) -> dict[str, str]:
        _, certificate = self._load_signing_material()
        merchant_hint = ""
        try:
            common_name = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            if "@" in common_name:
                parts = common_name.split("@")
                if len(parts) >= 3:
                    merchant_hint = parts[2].split(":")[0]
        except Exception:  # noqa: BLE001
            merchant_hint = ""
        return {
            "cert_id": str(certificate.serial_number),
            "subject": certificate.subject.rfc4514_string(),
            "merchant_hint": merchant_hint,
        }

    def _read_binary(self, file_path: str) -> bytes:
        if not file_path:
            return b""
        try:
            with open(file_path, "rb") as file:
                return file.read()
        except FileNotFoundError:
            return b""

    def _sign(self, params: dict[str, str]) -> dict[str, str]:
        private_key, certificate = self._load_signing_material()
        signed = dict(params)
        signed["certId"] = str(certificate.serial_number)
        payload = "&".join(
            f"{key}={signed[key]}"
            for key in sorted(signed)
            if signed[key] is not None and signed[key] != "" and key != "signature"
        )
        digest_text = self._digest_text(payload, "sha256")
        signature = private_key.sign(
            digest_text.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signed["signature"] = base64.b64encode(signature).decode("utf-8")
        return signed

    def _verify(self, params: dict[str, str]) -> bool:
        signature = params.get("signature", "")
        if not signature:
            return False
        certificate = self._match_cert_by_cert_id(params.get("certId"))
        if certificate is None:
            return True
        if not self._is_trusted_by_chain(certificate):
            return False
        payload = "&".join(
            f"{key}={params[key]}"
            for key in sorted(params)
            if params[key] is not None and params[key] != "" and key != "signature"
        )
        digest_text = self._digest_text(payload, "sha256")
        try:
            certificate.public_key().verify(
                base64.b64decode(signature),
                digest_text.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception:  # noqa: BLE001
            return False

    def _base_params(self, *, order_no: str, amount: Decimal) -> dict[str, str]:
        now = datetime.now()
        normalized_order_no = self._normalize_id(order_no, prefix="ord")
        return {
            "version": "5.1.0",
            "encoding": "UTF-8",
            "signMethod": "01",
            "txnType": "01",
            "txnSubType": "01",
            "bizType": "000201",
            "channelType": "07",
            "accessType": "0",
            "currencyCode": "156",
            "merId": settings.unionpay_merchant_id,
            "orderId": normalized_order_no,
            "txnTime": now.strftime("%Y%m%d%H%M%S"),
            "txnAmt": _fen(amount),
            "frontUrl": settings.unionpay_front_url or settings.unionpay_back_url,
            "backUrl": settings.unionpay_back_url,
            "payTimeout": (now + timedelta(minutes=15)).strftime("%Y%m%d%H%M%S"),
        }

    def _post(self, url: str, params: dict[str, str]) -> dict[str, str]:
        try:
            response = httpx.post(
                url,
                data=params,
                timeout=20.0,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="银联请求失败，请检查支付配置或网关连通性",
            ) from exc
        parsed: dict[str, str] = {}
        for item in response.text.split("&"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            parsed[key] = value
        return parsed

    def create_payment(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> PaymentProviderResult:
        if (
            not settings.unionpay_merchant_id
            or not settings.unionpay_back_url
            or not settings.unionpay_front_trans_url
            or not settings.unionpay_sign_cert_path
            or not settings.unionpay_sign_cert_password
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="银联支付未配置完成")
        return PaymentProviderResult(
            channel_order_no=order_no,
            payment_url=f"/api/payments/unionpay/pay/{quote_plus(order_no)}",
        )

    def build_payment_page(
        self,
        *,
        order_no: str,
        amount: Decimal,
        subject: str,
    ) -> str:
        params = self._sign(self._base_params(order_no=order_no, amount=amount))
        inputs = "\n".join(
            f'<input type="hidden" name="{escape(key)}" value="{escape(value)}" />'
            for key, value in params.items()
        )
        action = escape(settings.unionpay_front_trans_url)
        title = escape(subject)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>跳转银联支付</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif; background: #f8fafc; color: #172033; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
      .card {{ width:min(92vw, 460px); background:#fff; border:1px solid #d8e0eb; border-radius:28px; padding:32px; box-shadow:0 18px 45px rgba(23,32,51,0.08); text-align:center; }}
      .title {{ font-size:28px; font-weight:700; margin-bottom:10px; }}
      .desc {{ font-size:15px; color:#667085; line-height:1.7; }}
      .button {{ margin-top:24px; display:inline-flex; justify-content:center; align-items:center; width:100%; height:54px; border-radius:18px; border:none; background:#315efb; color:#fff; font-size:18px; font-weight:700; cursor:pointer; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="title">跳转银联支付</div>
      <div class="desc">订单号：{escape(order_no)}<br/>正在打开银联收银台，如果没有自动跳转，请点击下方按钮。</div>
      <form id="unionpay-form" method="post" action="{action}">
        {inputs}
        <button class="button" type="submit">继续前往支付</button>
      </form>
    </div>
    <script>window.setTimeout(function () {{ document.getElementById('unionpay-form')?.submit(); }}, 300);</script>
  </body>
</html>"""

    def query_payment(self, *, order_no: str, channel_order_no: str | None = None) -> dict:
        params = self._sign(
            {
                "version": "5.1.0",
                "encoding": "UTF-8",
                "signMethod": "01",
                "txnType": "00",
                "txnSubType": "00",
                "bizType": "000201",
                "accessType": "0",
                "channelType": "07",
                "merId": settings.unionpay_merchant_id,
                "orderId": self._normalize_id(order_no, prefix="ord"),
                "txnTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            }
        )
        response = self._post(settings.unionpay_query_url, params)
        success = response.get("respCode") == "00" and response.get("origRespCode") == "00"
        return {
            "success": success,
            "status": "success" if success else "pending",
            "channel_order_no": response.get("queryId", channel_order_no),
            "raw": response,
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
        params = self._sign(
            {
                "version": "5.1.0",
                "encoding": "UTF-8",
                "signMethod": "01",
                "txnType": "04",
                "txnSubType": "00",
                "bizType": "000201",
                "channelType": "07",
                "accessType": "0",
                "currencyCode": "156",
                "merId": settings.unionpay_merchant_id,
                "orderId": self._normalize_id(refund_no, prefix="ref"),
                "txnTime": datetime.now().strftime("%Y%m%d%H%M%S"),
                "txnAmt": _fen(amount),
                "origQryId": channel_order_no or "",
                "backUrl": settings.unionpay_back_url,
            }
        )
        response = self._post(settings.unionpay_back_trans_url, params)
        if response.get("respCode") not in {"00", "03", "04", "05"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.get("respMsg") or "银联退款失败",
            )
        return {
            "success": response.get("respCode") == "00",
            "status": "success" if response.get("respCode") == "00" else "processing",
            "channel_order_no": channel_order_no,
            "channel_refund_no": response.get("queryId", refund_no),
            "raw": response,
        }

    def query_refund(
        self,
        *,
        order_no: str,
        refund_no: str,
        channel_order_no: str | None = None,
    ) -> dict:
        params = self._sign(
            {
                "version": "5.1.0",
                "encoding": "UTF-8",
                "signMethod": "01",
                "txnType": "00",
                "txnSubType": "00",
                "bizType": "000201",
                "accessType": "0",
                "channelType": "07",
                "merId": settings.unionpay_merchant_id,
                "orderId": self._normalize_id(refund_no, prefix="ref"),
                "txnTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            }
        )
        response = self._post(settings.unionpay_query_url, params)
        success = response.get("respCode") == "00" and response.get("origRespCode") == "00"
        return {
            "success": success,
            "status": "success" if success else "unknown",
            "channel_order_no": channel_order_no,
            "channel_refund_no": response.get("queryId", refund_no),
            "raw": response,
        }

    def parse_notify(self, *, headers: dict[str, Any], body: Any) -> dict:
        payload = {key: str(value) for key, value in dict(body).items()}
        if not self._verify(payload):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="银联回调验签失败")
        success = payload.get("respCode") == "00"
        return {
            "success": success,
            "order_no": payload.get("orderId", ""),
            "channel_order_no": payload.get("queryId", ""),
            "status": payload.get("respCode", ""),
            "raw": payload,
        }
