from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date
from app.models.patient import SexEnum

class PatientCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    doc_id: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_plan: Optional[str] = None
    insurance_member_id: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None
    user_id: Optional[str] = None

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    doc_id: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_plan: Optional[str] = None
    insurance_member_id: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None

class PatientOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    email: Optional[EmailStr] = None
    doc_id: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_plan: Optional[str] = None
    insurance_member_id: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None
    clinics: List[str] = []

    class Config:
        from_attributes = True

    @staticmethod
    def from_model(p) -> "PatientOut":
        """Construye seguro sin usar __dict__."""
        return PatientOut(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            email=p.email,
            doc_id=p.doc_id,
            phone=p.phone,
            notes=p.notes,
            insurance_provider=p.insurance_provider,
            insurance_plan=p.insurance_plan,
            insurance_member_id=p.insurance_member_id,
            photo_url=p.photo_url,
            sex=p.sex,
            birth_date=p.birth_date,
            clinics=[c.id for c in getattr(p, "clinics", [])],
        )