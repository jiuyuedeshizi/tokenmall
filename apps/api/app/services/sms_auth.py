import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsAuthServiceError(RuntimeError):
    pass


def sms_auth_delivery_configured() -> bool:
    return bool(
        settings.alibaba_cloud_sms_auth_enabled
        and settings.alibaba_cloud_access_key_id
        and settings.alibaba_cloud_access_key_secret
        and settings.alibaba_cloud_sms_sign_name
        and settings.alibaba_cloud_sms_template_code
        and settings.alibaba_cloud_sms_template_param
    )


def _build_client():
    try:
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dypnsapi20170525.client import Client as DypnsClient
    except ImportError as exc:
        raise SmsAuthServiceError("阿里云短信认证 SDK 未安装，请先安装依赖") from exc

    config = open_api_models.Config(
        access_key_id=settings.alibaba_cloud_access_key_id,
        access_key_secret=settings.alibaba_cloud_access_key_secret,
        region_id=settings.alibaba_cloud_sms_region,
    )
    return DypnsClient(config)


def _scheme_name_or_none() -> str | None:
    scheme_name = settings.alibaba_cloud_sms_scheme_name.strip()
    return scheme_name or None


def send_sms_auth_code(phone: str) -> str | None:
    if not sms_auth_delivery_configured():
        logger.info("阿里云短信认证未配置，跳过实际短信发送: %s", phone)
        return None

    try:
        from alibabacloud_dypnsapi20170525 import models as dypns_models
    except ImportError as exc:
        raise SmsAuthServiceError("阿里云短信认证 SDK 未安装，请先安装依赖") from exc

    request = dypns_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        country_code="86",
        scheme_name=_scheme_name_or_none(),
        sign_name=settings.alibaba_cloud_sms_sign_name,
        template_code=settings.alibaba_cloud_sms_template_code,
        template_param=settings.alibaba_cloud_sms_template_param,
        code_length=6,
        code_type=1,
        valid_time=300,
        interval=60,
        duplicate_policy=1,
        return_verify_code=settings.alibaba_cloud_sms_debug_return_demo_code,
    )

    try:
        response = _build_client().send_sms_verify_code(request)
    except Exception as exc:  # noqa: BLE001
        raise SmsAuthServiceError("阿里云短信认证发送失败，请稍后重试") from exc

    body = response.body
    if not body or not body.success or body.code != "OK":
        message = body.message if body and body.message else "阿里云短信认证发送失败，请稍后重试"
        raise SmsAuthServiceError(message)

    if body.model and body.model.verify_code:
        return body.model.verify_code
    return None


def verify_sms_auth_code(phone: str, code: str) -> bool:
    if not sms_auth_delivery_configured():
        logger.info("阿里云短信认证未配置，跳过实际短信校验: %s", phone)
        return False

    try:
        from alibabacloud_dypnsapi20170525 import models as dypns_models
    except ImportError as exc:
        raise SmsAuthServiceError("阿里云短信认证 SDK 未安装，请先安装依赖") from exc

    request = dypns_models.CheckSmsVerifyCodeRequest(
        phone_number=phone,
        country_code="86",
        scheme_name=_scheme_name_or_none(),
        verify_code=code,
    )

    try:
        response = _build_client().check_sms_verify_code(request)
    except Exception as exc:  # noqa: BLE001
        raise SmsAuthServiceError("阿里云短信认证校验失败，请稍后重试") from exc

    body = response.body
    if not body or not body.success or body.code != "OK":
        message = body.message if body and body.message else "阿里云短信认证校验失败，请稍后重试"
        raise SmsAuthServiceError(message)

    return bool(body.model and body.model.verify_result == "PASS")
