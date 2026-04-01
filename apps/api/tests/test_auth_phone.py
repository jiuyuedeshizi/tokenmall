from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import User, VerificationCode, WalletAccount
from app.schemas.auth import ChangePasswordRequest, PhoneLoginRequest, VerifyEmailRequest
from app.services.auth import change_user_password, login_user_by_phone_code, send_phone_login_code, send_register_email_verification_code, verify_user_email


def _seed_user(sync_session_factory, *, email: str, phone: str) -> None:
    db = sync_session_factory()
    try:
        db.add(
            User(
                email=email,
                phone=phone,
                password_hash="hashed",
                name="Tester",
                role="user",
                status="active",
                email_verified=True,
            )
        )
        db.flush()
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        db.add(WalletAccount(user_id=user.id))
        db.commit()
    finally:
        db.close()


def test_send_phone_code_returns_demo_code_and_persists_record(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="phone@example.com", phone="13800000010")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)

        result = send_phone_login_code("13800000010", db)

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "phone",
                VerificationCode.target == "13800000010",
            )
        ).scalar_one()
        assert result.success is True
        assert result.demo_code is not None
        assert result.cooldown_seconds == 60
        assert result.message == "验证码已发送，请查收"
        assert record.code_hash
    finally:
        db.close()


def test_login_user_by_phone_code_consumes_local_code(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="consume@example.com", phone="13800000011")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)
        code_result = send_phone_login_code("13800000011", db)

        login_result = login_user_by_phone_code(
            PhoneLoginRequest(phone="13800000011", code=code_result.demo_code or ""),
            db,
        )

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "phone",
                VerificationCode.target == "13800000011",
            )
        ).scalar_one()
        assert login_result.access_token
        assert record.code_hash == ""
        assert record.consumed_at is not None
    finally:
        db.close()


def test_phone_login_uses_aliyun_sms_auth_when_enabled(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="aliyun@example.com", phone="13800000012")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: True)
        monkeypatch.setattr("app.services.auth.verify_sms_auth_code", lambda phone, code: phone == "13800000012" and code == "123456")

        login_result = login_user_by_phone_code(
            PhoneLoginRequest(phone="13800000012", code="123456"),
            db,
        )

        assert login_result.access_token
        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "phone",
                VerificationCode.target == "13800000012",
            )
        ).scalar_one_or_none()
        assert record is None
    finally:
        db.close()


def test_phone_login_rejects_invalid_aliyun_code(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="invalid@example.com", phone="13800000013")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: True)
        monkeypatch.setattr("app.services.auth.verify_sms_auth_code", lambda phone, code: False)

        with pytest.raises(HTTPException) as exc_info:
            login_user_by_phone_code(
                PhoneLoginRequest(phone="13800000013", code="000000"),
                db,
            )

        assert exc_info.value.status_code == 400
        assert "已失效" in str(exc_info.value.detail)
    finally:
        db.close()


def test_phone_login_auto_registers_new_user(sync_session_factory, monkeypatch):
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)
        code_result = send_phone_login_code("13800000014", db)

        login_result = login_user_by_phone_code(
            PhoneLoginRequest(phone="13800000014", code=code_result.demo_code or ""),
            db,
        )

        user = db.execute(select(User).where(User.phone == "13800000014")).scalar_one()
        assert login_result.access_token
        assert user.email is None
        assert user.name == "用户0014"
        assert user.has_password is False
        assert user.profile_completed is False
    finally:
        db.close()


def test_phone_only_user_can_set_password_without_current_password(sync_session_factory, monkeypatch):
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)
        code_result = send_phone_login_code("13800000015", db)
        login_user_by_phone_code(PhoneLoginRequest(phone="13800000015", code=code_result.demo_code or ""), db)

        user = db.execute(select(User).where(User.phone == "13800000015")).scalar_one()
        change_user_password(user, ChangePasswordRequest(new_password="Password123", current_password=None), db)

        db.refresh(user)
        assert user.has_password is True
    finally:
        db.close()


def test_phone_only_user_can_bind_unique_email(sync_session_factory, monkeypatch):
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        code_result = send_phone_login_code("13800000016", db)
        login_user_by_phone_code(PhoneLoginRequest(phone="13800000016", code=code_result.demo_code or ""), db)

        user = db.execute(select(User).where(User.phone == "13800000016")).scalar_one()
        send_result = send_register_email_verification_code(user, "bind@example.com", db)
        verify_user_email(user, VerifyEmailRequest(email="bind@example.com", code=send_result.demo_code or ""), db)

        db.refresh(user)
        assert user.email == "bind@example.com"
        assert user.email_verified is True
    finally:
        db.close()


def test_phone_only_user_merges_into_existing_email_account(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="merge@example.com", phone="13800000017")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.sms_auth_delivery_configured", lambda: False)
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)

        existing_user = db.execute(select(User).where(User.email == "merge@example.com")).scalar_one()
        existing_user.phone = None
        db.commit()

        code_result = send_phone_login_code("13800000018", db)
        login_user_by_phone_code(PhoneLoginRequest(phone="13800000018", code=code_result.demo_code or ""), db)
        phone_user = db.execute(select(User).where(User.phone == "13800000018")).scalar_one()

        send_result = send_register_email_verification_code(phone_user, "merge@example.com", db)
        verify_result = verify_user_email(
            phone_user,
            VerifyEmailRequest(email="merge@example.com", code=send_result.demo_code or ""),
            db,
        )

        merged_user = db.execute(select(User).where(User.email == "merge@example.com")).scalar_one()
        deleted_phone_user = db.execute(select(User).where(User.id == phone_user.id)).scalar_one_or_none()
        assert verify_result.access_token
        assert merged_user.phone == "13800000018"
        assert deleted_phone_user is None
    finally:
        db.close()
