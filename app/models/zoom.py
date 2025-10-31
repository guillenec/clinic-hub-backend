# app/models/zoom.py
from __future__ import annotations
import datetime as dt
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

if TYPE_CHECKING:
    from app.models.user import User  # solo para hints (no se ejecuta en runtime)


class ZoomToken(Base):
    __tablename__ = "zoom_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="zoom_token", uselist=False)


class AppointmentZoom(Base):
    __tablename__ = "appointment_zooms"

    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id", ondelete="CASCADE"), primary_key=True
    )
    meeting_id: Mapped[str] = mapped_column(String(64), nullable=False)
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    join_url: Mapped[str] = mapped_column(Text, nullable=False)
    passcode: Mapped[str] = mapped_column(String(32), default="", nullable=False)
