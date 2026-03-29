from decimal import Decimal
from datetime import datetime, timedelta
import random

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, WalletAccount
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PhoneLoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
)

PHONE_CODE_STORE: dict[str, tuple[str, datetime]] = {}


def register_user(payload: RegisterRequest, db: Session) -> TokenResponse:
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已注册")
    phone_exists = db.query(User).filter(User.phone == payload.phone).first()
    if phone_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已注册")

    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="user",
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(WalletAccount(user_id=user.id, balance=Decimal("0.0000"), currency="CNY"))
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


def login_user(payload: LoginRequest, db: Session) -> TokenResponse:
    identifier = payload.identifier.strip()
    user = db.query(User).filter((User.email == identifier) | (User.phone == identifier)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    return TokenResponse(access_token=create_access_token(str(user.id)))


def send_phone_login_code(phone: str, db: Session) -> dict[str, bool | str]:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该手机号尚未注册")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.now() + timedelta(minutes=5)
    PHONE_CODE_STORE[phone] = (code, expires_at)
    return {"success": True, "demo_code": code}


def login_user_by_phone_code(payload: PhoneLoginRequest, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该手机号尚未注册")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")

    stored = PHONE_CODE_STORE.get(payload.phone)
    if not stored:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先获取验证码")

    code, expires_at = stored
    if datetime.now() > expires_at:
        PHONE_CODE_STORE.pop(payload.phone, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码已过期，请重新获取")
    if payload.code != code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误")

    PHONE_CODE_STORE.pop(payload.phone, None)
    return TokenResponse(access_token=create_access_token(str(user.id)))


def update_user_profile(user: User, payload: UpdateProfileRequest, db: Session) -> User:
    user.name = payload.name
    db.commit()
    db.refresh(user)
    return user


def change_user_password(user: User, payload: ChangePasswordRequest, db: Session) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


def admin_reset_password(user: User, new_password: str, db: Session) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()
