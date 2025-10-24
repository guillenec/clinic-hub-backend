import uuid
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    doctors = relationship("Doctor", secondary="clinic_doctors", back_populates="clinics")
    patients = relationship("Patient", secondary="clinic_patients", back_populates="clinics")
