from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PhoneLoginRequest,
    RegisterRequest,
    SendPhoneCodeRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserInfo,
)
from app.services.auth import (
    change_user_password,
    login_user,
    login_user_by_phone_code,
    register_user,
    send_phone_login_code,
    update_user_profile,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return login_user(payload, db)


@router.post("/send-phone-code")
def send_login_phone_code(payload: SendPhoneCodeRequest, db: Session = Depends(get_db)):
    return send_phone_login_code(payload.phone, db)


@router.post("/login-phone", response_model=TokenResponse)
def login_phone(payload: PhoneLoginRequest, db: Session = Depends(get_db)):
    return login_user_by_phone_code(payload, db)


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
