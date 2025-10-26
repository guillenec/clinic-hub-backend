from __future__ import annotations
from datetime import datetime, date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Date, DateTime, Boolean, ForeignKey, Integer
from app.core.db import Base

class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("doctors.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)

    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50))

    reason: Mapped[str | None] = mapped_column(Text)
    rest_days: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    include_signature: Mapped[bool] = mapped_column(Boolean, default=True)
    include_stamp: Mapped[bool] = mapped_column(Boolean, default=True)

    # igual que arriba: a JSON si podés
    render_json: Mapped[str | None] = mapped_column(Text)

    verify_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

