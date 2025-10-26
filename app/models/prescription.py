from __future__ import annotations
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Date, DateTime, Boolean, ForeignKey, Integer
from app.core.db import Base

class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid hex o uuid4 string
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)

    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    include_signature: Mapped[bool] = mapped_column(Boolean, default=True)
    include_stamp: Mapped[bool] = mapped_column(Boolean, default=True)

    # si tu MySQL/MariaDB soporta JSON, cambiá a JSON; si no, dejalo Text
    render_json: Mapped[str | None] = mapped_column(Text)

    verify_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["PrescriptionItem"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan"
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prescription_id: Mapped[str] = mapped_column(ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True)

    position: Mapped[int] = mapped_column(Integer, default=0)  # por si querés ordenar
    drug: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(255))
    frequency: Mapped[str] = mapped_column(String(255))
    duration: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    prescription: Mapped["Prescription"] = relationship(back_populates="items")
