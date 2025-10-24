from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

ApptType = Literal["presencial", "virtual"]
ApptStatus = Literal["pending", "confirmed", "cancelled"]

class AppointmentCreate(BaseModel):
    doctor_id: Optional[str] = None        # si el que crea es doctor, puede omitirse
    patient_id: str
    clinic_id: str
    starts_at: datetime = Field(..., description="ISO datetime (UTC o local coherente)")
    ends_at:   datetime
    type: ApptType = "presencial"
    status: ApptStatus = "pending"

class AppointmentUpdate(BaseModel):
    patient_id: Optional[str] = None
    clinic_id: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    type: Optional[ApptType] = None
    status: Optional[ApptStatus] = None

class AppointmentOut(BaseModel):
    id: str
    doctor_id: str
    patient_id: str
    clinic_id: str
    starts_at: datetime
    ends_at: datetime
    type: ApptType
    status: ApptStatus

    class Config:
        from_attributes = True
