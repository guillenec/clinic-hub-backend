import uuid
import enum
from sqlalchemy import String, Enum, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class SexEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doc_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # DNI/Documento
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # insurance snapshot (simple columnas; si querés JSON, luego migramos a JSON con MySQL 5.7+)
    insurance_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_plan: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_member_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sex: Mapped[SexEnum | None] = mapped_column(Enum(SexEnum), nullable=True)
    birth_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    clinics = relationship("Clinic", secondary="clinic_patients", back_populates="patients")
