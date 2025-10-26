from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, StringConstraints

# Atajo para string “no vacío y sin espacios alrededor”
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


# ------ Sub-modelos reutilizables ------
class DoctorAsset(BaseModel):
    id: str
    name: str
    license: Optional[str] = None
    signature_png: Optional[str] = None
    stamp_png: Optional[str] = None


class PatientMini(BaseModel):
    id: str
    name: str
    dni: Optional[str] = None


# ------ Ítems de la receta ------
class PrescriptionItemIn(BaseModel):
    drug: NonEmptyStr        # p.ej. "paracetamol"
    dose: NonEmptyStr        # p.ej. "500 mg"
    frequency: NonEmptyStr   # p.ej. "cada 8 h"
    duration: NonEmptyStr    # p.ej. "7 días"
    notes: Optional[str] = None  # marca u observaciones


# ------ Entrada (create) ------
class PrescriptionCreate(BaseModel):
    patient_id: str
    doctor_id: str
    issued_date: date
    # Para listas, sí podés usar Field(min_length=1) en v2:
    items: List[PrescriptionItemIn] = Field(..., min_length=1)
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    include_signature: bool = True
    include_stamp: bool = True


# ------ Salida (para el front) ------
class PrescriptionOut(BaseModel):
    id: str
    issued_date: date
    created_at: datetime
    patient: PatientMini
    doctor: DoctorAsset
    items: List[PrescriptionItemIn]
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    include_signature: bool
    include_stamp: bool
    render: dict          # payload para que el front genere PDF
    verify_code: str
    verify_url: str
