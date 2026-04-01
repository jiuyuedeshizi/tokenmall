from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str = Field(pattern=r"^1\d{10}$")
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=50)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str


class CodeSendResponse(BaseModel):
    success: bool
    demo_code: str | None = None
    message: str | None = None
    cooldown_seconds: int | None = None


class RegisterResponse(CodeSendResponse):
    email: EmailStr
    requires_email_verification: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SendPhoneCodeRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")


class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=4, max_length=8)


class SendEmailCodeRequest(BaseModel):
    email: EmailStr


class EmailLoginRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class UserInfo(BaseModel):
    id: int
    email: EmailStr | None = None
    phone: str | None = None
    name: str
    role: str
    status: str
    email_verified: bool
    has_password: bool
    profile_completed: bool

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str | None = Field(default=None, min_length=8)
    new_password: str = Field(min_length=8)
