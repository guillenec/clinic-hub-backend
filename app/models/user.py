import enum
import uuid
from sqlalchemy import String, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
from sqlalchemy.orm import relationship

class RoleEnum(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    zoom_token = relationship(
    "ZoomToken",
    back_populates="user",
    uselist=False,
    cascade="all, delete-orphan"
)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.patient)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Para 2FA (lo activaremos luego)
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    twofa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
