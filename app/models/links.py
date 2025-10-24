from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class ClinicDoctor(Base):
    __tablename__ = "clinic_doctors"
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), primary_key=True)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), primary_key=True)

class ClinicPatient(Base):
    __tablename__ = "clinic_patients"
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), primary_key=True)
