from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, Literal

# --- Consultations ---
class ConsultationCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str] = None
    date: Optional[datetime] = None
    specialty: str
    diagnosis: str
    notes: Optional[str] = None

class ConsultationUpdate(BaseModel):
    patient_id: str | None = None
    doctor_id: str | None = None
    appointment_id: str | None = None
    date: datetime | None = None
    specialty: str | None = None
    diagnosis: str | None = None
    notes: str | None = None

class ConsultationOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str] = None
    date: datetime
    specialty: str
    diagnosis: str
    notes: Optional[str] = None
    class Config:
        from_attributes = True

# --- Medications ---
MedStatus = Literal["active", "suspended", "completed"]

class MedicationCreate(BaseModel):
    patient_id: str
    name: str
    dosage: str
    frequency: str
    status: MedStatus = "active"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    status: Optional[MedStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class MedicationOut(BaseModel):
    id: str
    patient_id: str
    name: str
    dosage: str
    frequency: str
    status: MedStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    class Config:
        from_attributes = True

# ---------- LABS ----------
LabStatus = Literal["pending", "complete"]

class LabCreate(BaseModel):
    patient_id: str
    test: str
    date: Optional[datetime] = None
    result: Optional[str] = ""
    status: LabStatus = "pending"

class LabUpdate(BaseModel):
    test: Optional[str] = None
    date: Optional[datetime] = None
    result: Optional[str] = None
    status: Optional[LabStatus] = None

class LabOut(BaseModel):
    id: str
    patient_id: str
    test: str
    date: datetime
    result: str
    status: LabStatus
    class Config:
        from_attributes = True

# ---------- VITALS ----------
VitalStatus = Literal["Normal", "Alto", "Bajo"]

class VitalCreate(BaseModel):
    patient_id: str
    metric: str
    value: str
    date: Optional[datetime] = None
    status: Optional[VitalStatus] = None

class VitalUpdate(BaseModel):
    metric: Optional[str] = None
    value: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[VitalStatus] = None

class VitalOut(BaseModel):
    id: str
    patient_id: str
    metric: str
    value: str
    date: datetime
    status: Optional[VitalStatus] = None
    class Config:
        from_attributes = True