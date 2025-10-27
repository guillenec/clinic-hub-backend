from __future__ import annotations
from typing import Optional
from datetime import date, datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Date, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doctor_id:  Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)

    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    type:        Mapped[str]  = mapped_column(String(50))
    reason:      Mapped[Optional[str]] = mapped_column(Text, default=None)
    rest_days:   Mapped[Optional[int]] = mapped_column(Integer, default=None)
    start_date:  Mapped[Optional[date]] = mapped_column(Date, default=None)
    end_date:    Mapped[Optional[date]] = mapped_column(Date, default=None)
    notes:       Mapped[Optional[str]] = mapped_column(Text, default=None)

    include_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    include_stamp:     Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    render_json: Mapped[Optional[str]] = mapped_column(Text, default=None)
    verify_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)

    created_at:  Mapped[datetime] = mapped_column(DateTime(), server_default=func.current_timestamp(), nullable=False)
