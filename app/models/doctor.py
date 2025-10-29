import uuid
import enum
from sqlalchemy import String, Enum, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class SexEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    specialty: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # signature_png: Mapped[str | None] = mapped_column(String(255), nullable=True)  # url
    # stamp_png: Mapped[str | None] = mapped_column(String(255), nullable=True)      # url
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sex: Mapped[SexEnum | None] = mapped_column(Enum(SexEnum), nullable=True)
    birth_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    clinics = relationship("Clinic", secondary="clinic_doctors", back_populates="doctors")
    
    signature_png: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    signature_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    stamp_png: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stamp_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)