from email.message import EmailMessage
import logging
import smtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


def email_delivery_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_login_code_email(email: str, code: str) -> None:
    if not email_delivery_configured():
        logger.info("SMTP 未配置，跳过实际邮件发送: %s", email)
        return

    message = EmailMessage()
    sender = settings.smtp_from_email
    if settings.smtp_from_name:
        sender = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"

    message["Subject"] = "TokenMall 登录验证码"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "您好，",
                "",
                f"您本次的 TokenMall 登录验证码为：{code}",
                "验证码 5 分钟内有效，请勿泄露给他人。",
            ]
        )
    )

    smtp_class: type[smtplib.SMTP] = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if not settings.smtp_use_ssl and settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
