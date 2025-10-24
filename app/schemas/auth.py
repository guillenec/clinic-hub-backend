from pydantic import BaseModel, EmailStr, Field
from enum import Enum

class Role(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

class RegisterIn(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Role

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    otp: str | None = None   # <-- OTP opcional, requerido si 2FA activo

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: Role
    is_active: bool

    class Config:
        from_attributes = True

# --- 2FA ---
class TwoFASetupOut(BaseModel):
    secret: str
    otpauth_url: str
    qr_base64_png: str | None = None  # si instalaste qrcode

class TwoFAVerifyIn(BaseModel):
    otp: str

class TwoFADisableIn(BaseModel):
    otp: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut




