from __future__ import annotations

import smtplib

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import User, VerificationCode, WalletAccount
from app.schemas.auth import EmailLoginRequest, RegisterRequest, VerifyEmailRequest
from app.services import auth as auth_service
from app.services.auth import login_user_by_email_code, register_user, send_email_login_code, verify_user_email


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


def test_send_email_code_returns_demo_code_and_persists_record(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="mail@example.com", phone="13800000002")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)

        result = send_email_login_code("MAIL@example.com", db)

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "email",
                VerificationCode.target == "mail@example.com",
            )
        ).scalar_one()
        assert result.success is True
        assert result.demo_code is not None
        assert result.cooldown_seconds == 60
        assert result.message == "验证码已发送，请查收"
        assert record.code_hash
        assert record.send_attempts_in_window == 1
    finally:
        db.close()


def test_register_user_logs_in_directly_and_verify_success(sync_session_factory, monkeypatch):
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        result = register_user(
            RegisterRequest(
                email="newuser@example.com",
                phone="13800000008",
                password="Password123",
                name="New User",
            ),
            db,
        )

        user = db.execute(select(User).where(User.email == "newuser@example.com")).scalar_one()
        assert result.access_token
        assert user.email_verified is False

        resend_result = auth_service.send_register_email_verification_code(user, "newuser@example.com", db)
        assert resend_result.demo_code is not None

        verify_result = verify_user_email(
            user,
            VerifyEmailRequest(email="newuser@example.com", code=resend_result.demo_code or ""),
            db,
        )

        db.refresh(user)
        assert verify_result.access_token
        assert user.email_verified is True
        assert user.email_verified_at is not None
    finally:
        db.close()


def test_unverified_user_cannot_request_email_login_code(sync_session_factory, monkeypatch):
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        register_user(
            RegisterRequest(
                email="pending@example.com",
                phone="13800000009",
                password="Password123",
                name="Pending User",
            ),
            db,
        )

        with pytest.raises(HTTPException) as exc_info:
            send_email_login_code("pending@example.com", db)

        assert exc_info.value.status_code == 403
        assert "尚未验证" in str(exc_info.value.detail)
    finally:
        db.close()


def test_login_user_by_email_code_accepts_normalized_email(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="caseuser@example.com", phone="13800000003")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        code_result = send_email_login_code("caseuser@example.com", db)

        login_result = login_user_by_email_code(
            EmailLoginRequest(email="CASEUSER@example.com", code=code_result.demo_code or ""),
            db,
        )

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "email",
                VerificationCode.target == "caseuser@example.com",
            )
        ).scalar_one()
        assert login_result.access_token
        assert record.code_hash == ""
        assert record.consumed_at is not None
    finally:
        db.close()


def test_send_email_code_enforces_cooldown(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="cooldown@example.com", phone="13800000005")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        first = send_email_login_code("cooldown@example.com", db)
        assert first.demo_code

        with pytest.raises(HTTPException) as exc_info:
            send_email_login_code("cooldown@example.com", db)

        assert exc_info.value.status_code == 429
        assert "请求过于频繁" in str(exc_info.value.detail)
    finally:
        db.close()


def test_login_user_by_email_code_locks_after_too_many_attempts(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="attempts@example.com", phone="13800000006")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: False)
        send_email_login_code("attempts@example.com", db)

        for _ in range(4):
            with pytest.raises(HTTPException) as exc_info:
                login_user_by_email_code(
                    EmailLoginRequest(email="attempts@example.com", code="000000"),
                    db,
                )
            assert "还可再试" in str(exc_info.value.detail)

        with pytest.raises(HTTPException) as exc_info:
            login_user_by_email_code(
                EmailLoginRequest(email="attempts@example.com", code="000000"),
                db,
            )

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "email",
                VerificationCode.target == "attempts@example.com",
            )
        ).scalar_one()
        assert "错误次数过多" in str(exc_info.value.detail)
        assert record.code_hash == ""
    finally:
        db.close()


def test_send_email_code_raises_when_smtp_send_fails(sync_session_factory, monkeypatch):
    _seed_user(sync_session_factory, email="smtp@example.com", phone="13800000004")
    db = sync_session_factory()
    try:
        monkeypatch.setattr("app.services.auth.email_delivery_configured", lambda: True)

        def raise_smtp_error(email: str, code: str) -> None:  # noqa: ARG001
            raise smtplib.SMTPException("boom")

        monkeypatch.setattr("app.services.auth.send_login_code_email", raise_smtp_error)

        with pytest.raises(HTTPException) as exc_info:
            send_email_login_code("smtp@example.com", db)

        record = db.execute(
            select(VerificationCode).where(
                VerificationCode.channel == "email",
                VerificationCode.target == "smtp@example.com",
            )
        ).scalar_one_or_none()
        assert exc_info.value.status_code == 502
        assert "邮件发送失败" in str(exc_info.value.detail)
        assert record is None
    finally:
        db.close()
