# app/models/recovery_code.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, DateTime, Boolean, func
from app.db import Base

class RecoveryCode(Base):
    __tablename__ = "recovery_codes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)   # almacena **hash** (bcrypt/argon2)
    used: Mapped[bool] = mapped_column(default=False, nullable=False)
    used_at: Mapped[DateTime | None] = mapped_column(nullable=True)
    created_at: Mapped[DateTime] = mapped_column(server_default=func.now(), nullable=False)

# En tu User:
# - is_2fa_enabled: bool
# - totp_secret (encriptado / KMS); opcionalmente: totp_confirmed_at, last_2fa_disable_at
