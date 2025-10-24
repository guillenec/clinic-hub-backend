from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import jwt

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, extra: Optional[dict] = None, expires_minutes: int | None = None) -> str:
    to_encode = {"sub": subject, "iat": datetime.now(tz=timezone.utc)}
    if extra:
        to_encode.update(extra)
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# --- 2FA helpers ---
import base64
from io import BytesIO
import pyotp

def generate_2fa_secret() -> str:
    # 32 chars base32 (TOTP)
    return pyotp.random_base32(length=32)

def totp_uri_from_secret(secret: str, email: str, issuer: str = "Clinic Hub") -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)

def verify_totp(otp: str, secret: str) -> bool:
    try:
        return pyotp.TOTP(secret).verify(otp, valid_window=1)
    except Exception:
        return False

# Opcional: QR PNG en base64
def qr_png_base64_from_text(text: str) -> str:
    try:
        import qrcode
        img = qrcode.make(text)          # -> PIL.Image.Image
        buf = BytesIO()
        img.save(buf, "PNG")             # usa argumento posicional (silencia a Pylance)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""
