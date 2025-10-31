from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date
from app.models.doctor import SexEnum

class DoctorCreate(BaseModel):
    name: str
    specialty: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    color: Optional[str] = None
    license: Optional[str] = None
    signature_png: Optional[str] = None
    stamp_png: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None
    user_id: Optional[str] = None

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    color: Optional[str] = None
    license: Optional[str] = None
    signature_png: Optional[str] = None
    stamp_png: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None

class DoctorOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    specialty: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    color: Optional[str] = None
    license: Optional[str] = None
    signature_png: Optional[str] = None
    stamp_png: Optional[str] = None
    photo_url: Optional[str] = None
    sex: Optional[SexEnum] = None
    birth_date: Optional[date] = None
    clinics: List[str] = []

    class Config:
        from_attributes = True  # permite pasarle un modelo ORM

    @staticmethod
    def from_model(d) -> "DoctorOut":
        """Construye seguro sin usar __dict__."""
        return DoctorOut(
            id=d.id,
            user_id=d.user_id,
            name=d.name,
            specialty=d.specialty,
            email=d.email,
            phone=d.phone,
            color=d.color,
            license=d.license,
            signature_png=d.signature_png,
            stamp_png=d.stamp_png,
            photo_url=d.photo_url,
            sex=d.sex,
            birth_date=d.birth_date,
            clinics=[c.id for c in getattr(d, "clinics", [])],
        )
