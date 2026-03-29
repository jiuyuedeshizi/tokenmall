from fastapi import HTTPException, status

from app.services.payments.alipay import AlipayProvider
from app.services.payments.base import PaymentProvider
from app.services.payments.unionpay import UnionPayProvider
from app.services.payments.wechat import WechatPayProvider


def create_payment_provider(method: str) -> PaymentProvider:
    if method == "alipay":
        return AlipayProvider()
    if method == "wechat":
        return WechatPayProvider()
    if method == "unionpay":
        return UnionPayProvider()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="暂不支持该支付方式")
