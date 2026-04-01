from decimal import Decimal
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import random
import smtplib

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import (
    ApiKey,
    PaymentOrder,
    RefundRequest,
    UsageLog,
    UsageReservation,
    User,
    VerificationCode,
    WalletAccount,
    WalletLedger,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    CodeSendResponse,
    EmailLoginRequest,
    LoginRequest,
    PhoneLoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    VerifyEmailRequest,
)
from app.services.email import email_delivery_configured, send_login_code_email
from app.services.sms_auth import SmsAuthServiceError, send_sms_auth_code, sms_auth_delivery_configured, verify_sms_auth_code

CODE_PURPOSE_LOGIN = "login"
CODE_PURPOSE_VERIFY_EMAIL = "verify_email"
CODE_EXPIRE_MINUTES = 5
CODE_SEND_COOLDOWN_SECONDS = 60
CODE_SEND_LIMIT_WINDOW_MINUTES = 30
CODE_SEND_LIMIT_PER_WINDOW = 5
CODE_VERIFY_MAX_ATTEMPTS = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_verification_code(value: str) -> str:
    return hashlib.sha256(f"{settings.jwt_secret}:{value}".encode("utf-8")).hexdigest()


def _verify_code_hash(raw_code: str, hashed_code: str) -> bool:
    return hmac.compare_digest(_hash_verification_code(raw_code), hashed_code)


def _build_code_send_response(code: str | None = None) -> CodeSendResponse:
    return CodeSendResponse(
        success=True,
        demo_code=code,
        message="验证码已发送，请查收",
        cooldown_seconds=CODE_SEND_COOLDOWN_SECONDS,
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _seconds_until(target_time: datetime, now: datetime) -> int:
    return max(1, int((target_time - now).total_seconds()))


def _normalize_record_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_or_create_verification_code(channel: str, target: str, purpose: str, db: Session) -> VerificationCode:
    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.channel == channel,
            VerificationCode.target == target,
            VerificationCode.purpose == purpose,
        )
        .first()
    )
    if record:
        return record

    record = VerificationCode(channel=channel, target=target, purpose=purpose)
    db.add(record)
    db.flush()
    return record


def _issue_verification_code(channel: str, target: str, purpose: str, db: Session) -> str:
    now = _utcnow()
    record = _get_or_create_verification_code(channel, target, purpose, db)
    cooldown_until = _normalize_record_datetime(record.cooldown_until)
    send_window_started_at = _normalize_record_datetime(record.send_window_started_at)

    if cooldown_until and cooldown_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，请在 {_seconds_until(cooldown_until, now)} 秒后重试",
        )

    if not send_window_started_at or now - send_window_started_at >= timedelta(
        minutes=CODE_SEND_LIMIT_WINDOW_MINUTES
    ):
        record.send_window_started_at = now
        record.send_attempts_in_window = 0

    if record.send_attempts_in_window >= CODE_SEND_LIMIT_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{CODE_SEND_LIMIT_WINDOW_MINUTES} 分钟内最多发送 {CODE_SEND_LIMIT_PER_WINDOW} 次验证码，请稍后再试",
        )

    code = f"{random.randint(0, 999999):06d}"
    record.code_hash = _hash_verification_code(code)
    record.expires_at = now + timedelta(minutes=CODE_EXPIRE_MINUTES)
    record.cooldown_until = now + timedelta(seconds=CODE_SEND_COOLDOWN_SECONDS)
    record.send_attempts_in_window += 1
    record.verify_attempts = 0
    record.consumed_at = None
    db.flush()
    return code


def _consume_verification_code(channel: str, target: str, purpose: str, code: str, db: Session) -> None:
    now = _utcnow()
    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.channel == channel,
            VerificationCode.target == target,
            VerificationCode.purpose == purpose,
        )
        .first()
    )
    if not record or not record.code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先获取验证码")

    if record.consumed_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已使用，请重新获取")

    expires_at = _normalize_record_datetime(record.expires_at)
    if not expires_at or now > expires_at:
        record.code_hash = ""
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取")

    if not _verify_code_hash(code, record.code_hash):
        record.verify_attempts += 1
        if record.verify_attempts >= CODE_VERIFY_MAX_ATTEMPTS:
            record.code_hash = ""
            record.expires_at = now
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误次数过多，请重新获取")
        db.commit()
        remaining_attempts = CODE_VERIFY_MAX_ATTEMPTS - record.verify_attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"验证码错误，还可再试 {remaining_attempts} 次",
        )

    record.consumed_at = now
    record.code_hash = ""
    record.verify_attempts = 0
    db.commit()


def _ensure_user_email_verified(user: User) -> None:
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱尚未验证，请先完成邮箱验证",
        )


def _build_generated_name(phone: str) -> str:
    return f"用户{phone[-4:]}"


def _create_phone_user(phone: str, db: Session) -> User:
    user = User(
        email=None,
        phone=phone,
        password_hash="",
        name=_build_generated_name(phone),
        role="user",
        status="active",
        email_verified=False,
    )
    db.add(user)
    db.flush()
    db.add(WalletAccount(user_id=user.id, balance=Decimal("0.0000"), reserved_balance=Decimal("0.0000"), currency="CNY"))
    db.flush()
    return user


def _merge_wallet_accounts(source_user: User, target_user: User, db: Session) -> None:
    source_wallet = db.query(WalletAccount).filter(WalletAccount.user_id == source_user.id).first()
    target_wallet = db.query(WalletAccount).filter(WalletAccount.user_id == target_user.id).first()

    if source_wallet and not target_wallet:
        target_wallet = WalletAccount(
            user_id=target_user.id,
            balance=Decimal("0.0000"),
            reserved_balance=Decimal("0.0000"),
            currency=source_wallet.currency,
        )
        db.add(target_wallet)
        db.flush()

    if source_wallet and target_wallet:
        target_wallet.balance = Decimal(target_wallet.balance) + Decimal(source_wallet.balance)
        target_wallet.reserved_balance = Decimal(target_wallet.reserved_balance) + Decimal(source_wallet.reserved_balance)
        db.delete(source_wallet)


def _merge_user_into_target(source_user: User, target_user: User, verified_email: str, db: Session) -> User:
    source_phone = source_user.phone

    if target_user.phone and source_user.phone and target_user.phone != source_user.phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已绑定其他手机号，无法自动合并")

    db.query(ApiKey).filter(ApiKey.user_id == source_user.id).update({"user_id": target_user.id}, synchronize_session=False)
    db.query(PaymentOrder).filter(PaymentOrder.user_id == source_user.id).update(
        {"user_id": target_user.id},
        synchronize_session=False,
    )
    db.query(UsageLog).filter(UsageLog.user_id == source_user.id).update({"user_id": target_user.id}, synchronize_session=False)
    db.query(UsageReservation).filter(UsageReservation.user_id == source_user.id).update(
        {"user_id": target_user.id},
        synchronize_session=False,
    )
    db.query(RefundRequest).filter(RefundRequest.user_id == source_user.id).update(
        {"user_id": target_user.id},
        synchronize_session=False,
    )
    db.query(WalletLedger).filter(WalletLedger.user_id == source_user.id).update(
        {"user_id": target_user.id},
        synchronize_session=False,
    )

    _merge_wallet_accounts(source_user, target_user, db)

    db.query(VerificationCode).filter(
        or_(
            VerificationCode.target == verified_email,
            VerificationCode.target == source_user.phone,
            VerificationCode.target == source_user.email,
        )
    ).delete(synchronize_session=False)

    source_user.phone = None
    source_user.email = None
    db.flush()

    target_user.email = verified_email
    target_user.email_verified = True
    target_user.email_verified_at = _utcnow()
    if source_phone and not target_user.phone:
        target_user.phone = source_phone
    if not target_user.has_password and source_user.has_password:
        target_user.password_hash = source_user.password_hash
    if target_user._uses_generated_name() and not source_user._uses_generated_name():
        target_user.name = source_user.name

    db.delete(source_user)
    db.commit()
    db.refresh(target_user)
    return target_user


def register_user(payload: RegisterRequest, db: Session) -> TokenResponse:
    normalized_email = _normalize_email(payload.email)
    exists = db.query(User).filter(User.email == normalized_email).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已注册")
    phone_exists = db.query(User).filter(User.phone == payload.phone).first()
    if phone_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已注册")

    user = User(
        email=normalized_email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="user",
        status="active",
        email_verified=False,
    )
    db.add(user)
    db.flush()
    db.add(WalletAccount(user_id=user.id, balance=Decimal("0.0000"), currency="CNY"))
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


def login_user(payload: LoginRequest, db: Session) -> TokenResponse:
    identifier = payload.identifier.strip()
    normalized_identifier = _normalize_email(identifier) if "@" in identifier else identifier
    user = db.query(User).filter((User.email == normalized_identifier) | (User.phone == normalized_identifier)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    return TokenResponse(access_token=create_access_token(str(user.id)))


def send_phone_login_code(phone: str, db: Session) -> CodeSendResponse:
    if sms_auth_delivery_configured():
        try:
            demo_code = send_sms_auth_code(phone)
        except SmsAuthServiceError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        return _build_code_send_response(demo_code)

    code = _issue_verification_code("phone", phone, CODE_PURPOSE_LOGIN, db)
    db.commit()
    return _build_code_send_response(code)


def send_email_login_code(email: str, db: Session) -> CodeSendResponse:
    normalized_email = _normalize_email(email)
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该邮箱尚未注册")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    _ensure_user_email_verified(user)
    code = _issue_verification_code("email", normalized_email, CODE_PURPOSE_LOGIN, db)
    try:
        if email_delivery_configured():
            send_login_code_email(normalized_email, code)
    except (OSError, smtplib.SMTPException) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="验证码邮件发送失败，请稍后重试") from exc
    db.commit()
    return _build_code_send_response(None if email_delivery_configured() else code)


def send_register_email_verification_code(current_user: User, email: str, db: Session) -> CodeSendResponse:
    normalized_email = _normalize_email(email)
    existing_user = db.query(User).filter(User.email == normalized_email, User.id != current_user.id).first()
    if existing_user and existing_user.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱不可用，请更换后重试")
    if existing_user and existing_user.phone and existing_user.phone != current_user.phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已绑定其他手机号，无法自动合并")
    if current_user.email == normalized_email and current_user.email_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已验证，请直接登录")

    code = _issue_verification_code("email", normalized_email, CODE_PURPOSE_VERIFY_EMAIL, db)
    try:
        if email_delivery_configured():
            send_login_code_email(normalized_email, code)
    except (OSError, smtplib.SMTPException) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="验证邮件发送失败，请稍后重试") from exc
    db.commit()
    return CodeSendResponse(
        success=True,
        demo_code=None if email_delivery_configured() else code,
        message="验证邮件已发送，请查收",
        cooldown_seconds=CODE_SEND_COOLDOWN_SECONDS,
    )


def verify_user_email(current_user: User, payload: VerifyEmailRequest, db: Session) -> TokenResponse:
    normalized_email = _normalize_email(payload.email)
    if current_user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    _consume_verification_code("email", normalized_email, CODE_PURPOSE_VERIFY_EMAIL, payload.code, db)
    existing_user = db.query(User).filter(User.email == normalized_email, User.id != current_user.id).first()
    if existing_user:
        merged_user = _merge_user_into_target(current_user, existing_user, normalized_email, db)
        return TokenResponse(access_token=create_access_token(str(merged_user.id)))

    current_user.email = normalized_email
    current_user.email_verified = True
    current_user.email_verified_at = _utcnow()
    db.commit()
    return TokenResponse(access_token=create_access_token(str(current_user.id)))


def login_user_by_phone_code(payload: PhoneLoginRequest, db: Session) -> TokenResponse:
    if sms_auth_delivery_configured():
        try:
            verified = verify_sms_auth_code(payload.phone, payload.code)
        except SmsAuthServiceError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        if not verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已失效")
    else:
        _consume_verification_code("phone", payload.phone, CODE_PURPOSE_LOGIN, payload.code, db)
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user and user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    if not user:
        user = _create_phone_user(payload.phone, db)
        db.commit()
        db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)))


def login_user_by_email_code(payload: EmailLoginRequest, db: Session) -> TokenResponse:
    normalized_email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该邮箱尚未注册")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    _ensure_user_email_verified(user)

    _consume_verification_code("email", normalized_email, CODE_PURPOSE_LOGIN, payload.code, db)
    return TokenResponse(access_token=create_access_token(str(user.id)))


def update_user_profile(user: User, payload: UpdateProfileRequest, db: Session) -> User:
    user.name = payload.name
    db.commit()
    db.refresh(user)
    return user


def change_user_password(user: User, payload: ChangePasswordRequest, db: Session) -> None:
    if user.has_password:
        if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")
    elif payload.current_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


def admin_reset_password(user: User, new_password: str, db: Session) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()
