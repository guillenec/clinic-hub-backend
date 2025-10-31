from sqlalchemy import String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class ClinicDoctor(Base):
    __tablename__ = "clinic_doctors"
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), primary_key=True)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), primary_key=True)

    __table_args__ = (
        # por si en el futuro quitás el PK compuesto
        UniqueConstraint("clinic_id", "doctor_id", name="uq_clinic_doctor"),
        Index("ix_clinic_doctor_clinic", "clinic_id"),
        Index("ix_clinic_doctor_doctor", "doctor_id"),
    )

class ClinicPatient(Base):
    __tablename__ = "clinic_patients"
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), primary_key=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "patient_id", name="uq_clinic_patient"),
        Index("ix_clinic_patient_clinic", "clinic_id"),
        Index("ix_clinic_patient_patient", "patient_id"),
    )