from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import date
from datetime import date, datetime  # 👈 agregar datetime

class CertificateCreate(BaseModel):
    patient_id: str
    doctor_id: str
    issued_date: date
    type: str
    reason: Optional[str] = None
    rest_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    include_signature: bool = True
    include_stamp: bool = True

class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    doctor_id: str
    issued_date: date
    type: str
    reason: Optional[str] = None
    rest_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    include_signature: bool
    include_stamp: bool
    render_json: Optional[str] = None
    verify_code: str
    created_at: datetime      # 👈 era str
    doctor: Optional[dict] = None

class CertificateUpdate(BaseModel):
    issued_date: Optional[date] = None
    type: Optional[str] = None
    reason: Optional[str] = None
    rest_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    include_signature: Optional[bool] = None
    include_stamp: Optional[bool] = None
    render_json: Optional[str] = None
