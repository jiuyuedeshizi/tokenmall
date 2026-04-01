from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    CodeSendResponse,
    EmailLoginRequest,
    LoginRequest,
    PhoneLoginRequest,
    RegisterRequest,
    SendEmailCodeRequest,
    SendPhoneCodeRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserInfo,
    VerifyEmailRequest,
)
from app.services.auth import (
    change_user_password,
    login_user,
    login_user_by_email_code,
    login_user_by_phone_code,
    register_user,
    send_register_email_verification_code,
    send_email_login_code,
    send_phone_login_code,
    update_user_profile,
    verify_user_email,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return login_user(payload, db)


@router.post("/send-phone-code", response_model=CodeSendResponse)
def send_login_phone_code(payload: SendPhoneCodeRequest, db: Session = Depends(get_db)):
    return send_phone_login_code(payload.phone, db)


@router.post("/send-email-code", response_model=CodeSendResponse)
def send_login_email_code(payload: SendEmailCodeRequest, db: Session = Depends(get_db)):
    return send_email_login_code(payload.email, db)


@router.post("/send-email-verification-code", response_model=CodeSendResponse)
def send_email_verification_code(
    payload: SendEmailCodeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return send_register_email_verification_code(current_user, payload.email, db)


@router.post("/login-phone", response_model=TokenResponse)
def login_phone(payload: PhoneLoginRequest, db: Session = Depends(get_db)):
    return login_user_by_phone_code(payload, db)


@router.post("/login-email", response_model=TokenResponse)
def login_email(payload: EmailLoginRequest, db: Session = Depends(get_db)):
    return login_user_by_email_code(payload, db)


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(
    payload: VerifyEmailRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return verify_user_email(current_user, payload, db)


@router.get("/me", response_model=UserInfo)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=UserInfo)
def update_profile(payload: UpdateProfileRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return update_user_profile(current_user, payload, db)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_user_password(current_user, payload, db)
    return {"success": True}
