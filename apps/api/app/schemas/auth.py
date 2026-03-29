from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str = Field(pattern=r"^1\d{10}$")
    password: str = Field(min_length=8)
    name: str = Field(min_length=2, max_length=50)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SendPhoneCodeRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")


class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    code: str = Field(min_length=4, max_length=8)


class UserInfo(BaseModel):
    id: int
    email: EmailStr
    phone: str | None = None
    name: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)
