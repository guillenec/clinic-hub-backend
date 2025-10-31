import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
import enum

class LabStatus(str, enum.Enum):
    pending = "pending"
    complete = "complete"

class LabResult(Base):
    __tablename__ = "lab_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    test: Mapped[str] = mapped_column(String(120))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    result: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[LabStatus] = mapped_column(Enum(LabStatus), default=LabStatus.pending, index=True)

class VitalStatus(str, enum.Enum):
    Normal = "Normal"
    Alto = "Alto"
    Bajo = "Bajo"

class Vital(Base):
    __tablename__ = "vitals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)
    metric: Mapped[str] = mapped_column(String(80))       # e.g. TA, FC, Peso
    value: Mapped[str] = mapped_column(String(120))       # e.g. "120/80 mmHg"
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[VitalStatus | None] = mapped_column(Enum(VitalStatus), nullable=True)
