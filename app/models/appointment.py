import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import relationship

from app.core.db import Base

class ApptType(str, enum.Enum):
    presencial = "presencial"
    virtual = "virtual"

class ApptStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"

class Appointment(Base):
    __tablename__ = "appointments"
    zoom_meeting = relationship(
    "AppointmentZoom",
    backref="appointment",
    uselist=False,
    cascade="all, delete-orphan"
)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), index=True)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    ends_at:   Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)

    type: Mapped[ApptType] = mapped_column(Enum(ApptType), default=ApptType.presencial)
    status: Mapped[ApptStatus] = mapped_column(Enum(ApptStatus), default=ApptStatus.pending)

    # opcional (para cargas selectivas)
    doctor = relationship("Doctor")
    patient = relationship("Patient")
    clinic = relationship("Clinic")
