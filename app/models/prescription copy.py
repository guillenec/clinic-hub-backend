from __future__ import annotations
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Date, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)

    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)

    include_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    include_stamp:     Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    # lo dejamos como TEXT para coincidir con tu migración (JSON serializado)
    render_json: Mapped[Optional[str]] = mapped_column(Text, default=None)

    verify_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime(), server_default=func.current_timestamp(), nullable=False)

    items: Mapped[List["PrescriptionItem"]] = relationship(
        back_populates="prescription",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PrescriptionItem.position",
    )

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prescription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    position:  Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    drug:      Mapped[str] = mapped_column(String(255))
    dose:      Mapped[str] = mapped_column(String(255))
    frequency: Mapped[str] = mapped_column(String(255))
    duration:  Mapped[str] = mapped_column(String(255))
    notes:     Mapped[Optional[str]] = mapped_column(Text, default=None)

    prescription: Mapped["Prescription"] = relationship(back_populates="items")
