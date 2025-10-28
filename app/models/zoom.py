from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR, DATETIME
from app.core.db import Base
from datetime import datetime

class ZoomToken(Base):
    __tablename__ = "zoom_tokens"
    user_id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True)  # tu user.id
    access_token: Mapped[str] = mapped_column(VARCHAR(2048))
    refresh_token: Mapped[str] = mapped_column(VARCHAR(2048))
    expires_at: Mapped[datetime] = mapped_column(DATETIME)  # UTC

class AppointmentZoom(Base):
    __tablename__ = "appointments_zoom"
    appointment_id: Mapped[str] = mapped_column(VARCHAR(36), primary_key=True)
    meeting_id:     Mapped[str] = mapped_column(VARCHAR(64), index=True)
    start_url:      Mapped[str] = mapped_column(VARCHAR(2048))  # host/doctor
    join_url:       Mapped[str] = mapped_column(VARCHAR(2048))  # paciente
    passcode:       Mapped[str] = mapped_column(VARCHAR(32))
