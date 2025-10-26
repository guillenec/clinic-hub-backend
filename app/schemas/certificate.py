from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from .prescription import PatientMini, DoctorAsset  # reutilizamos


class CertificateCreate(BaseModel):
    patient_id: str
    doctor_id: str
    issued_date: date = Field(..., description="Fecha del certificado (obligatoria)")
    type: str = Field(..., min_length=1, description="p.ej. 'medical_leave'")
    # Contenido opcional
    reason: Optional[str] = None
    rest_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    include_signature: bool = True
    include_stamp: bool = True


class CertificateOut(BaseModel):
    id: str
    issued_date: date
    created_at: datetime
    patient: PatientMini
    doctor: DoctorAsset
    # “certificate” lleva campos de negocio tal cual los necesita el front
    certificate: dict
    # payload libre para PDF (si lo usan)
    render: dict
    verify_code: str
    verify_url: str
