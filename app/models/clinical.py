import uuid
from datetime import datetime, date
from sqlalchemy import String, ForeignKey, DateTime, Enum, Date, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
import enum

class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    doctor_id:  Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True)
    # appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id"), nullable=True)
    appointment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    specialty: Mapped[str] = mapped_column(String(100))
    diagnosis: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class MedStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    completed = "completed"

class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    dosage: Mapped[str] = mapped_column(String(120))
    frequency: Mapped[str] = mapped_column(String(120))
    status: Mapped[MedStatus] = mapped_column(Enum(MedStatus), default=MedStatus.active, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date:   Mapped[date | None] = mapped_column(Date, nullable=True)
