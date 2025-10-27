from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime

class RxItemIn(BaseModel):
    drug: str
    dose: str
    frequency: str
    duration: str
    notes: Optional[str] = None

class PrescriptionCreate(BaseModel):
    patient_id: str
    doctor_id: str
    issued_date: date
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    items: List[RxItemIn] = Field(default_factory=list)
    include_signature: bool = True
    include_stamp: bool = True

class RxItemOut(RxItemIn):
    # 👇 ESTA LÍNEA ES LA CLAVE
    model_config = ConfigDict(from_attributes=True)
    id: int
    position: int

class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ya lo tenías, lo dejamos
    id: str
    issued_date: date
    created_at: datetime
    patient_id: str
    doctor_id: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    items: List[RxItemOut] = Field(default_factory=list)
    render_json: Optional[str] = None
    verify_code: str
    doctor: Optional[dict] = None

class RxItemPatch(BaseModel):
    id: Optional[int] = None      # para identificar el item existente (recomendado)
    position: Optional[int] = None
    drug: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    notes: Optional[str] = None

class PrescriptionUpdate(BaseModel):
    issued_date: Optional[date] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[RxItemPatch]] = None
    include_signature: Optional[bool] = None
    include_stamp: Optional[bool] = None
