from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.models.user import User

from jose import jwt, JWTError
from app.core.config import settings

# --- 2FA helpers ---
import base64
from io import BytesIO
import pyotp


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(
        subject: str, 
        extra: Optional[dict] = None, 
        expires_minutes: int | None = None
        ) -> str:
    to_encode = {"sub": subject, "iat": datetime.now(tz=timezone.utc)}
    if extra:
        to_encode.update(extra)
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

# --- 2FA functions ---

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

# -- Opcional: QR PNG en base64 --
def qr_png_base64_from_text(text: str) -> str:
    try:
        import qrcode
        img = qrcode.make(text)          # -> PIL.Image.Image
        buf = BytesIO()
        img.save(buf, "PNG")             # usa argumento posicional (silencia a Pylance)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""

# --- dependencia de FastAPI para obtener el usuario actual ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodifica el JWT recibido en el header Authorization y devuelve el usuario autenticado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # extrae el campo sub (id del usuario)
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # busca el usuario en la base
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user