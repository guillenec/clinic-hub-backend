from pydantic import BaseModel
from typing import Optional

class ClinicCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class ClinicOut(ClinicCreate):
    id: str
    class Config:
        from_attributes = True

class ClinicUpdate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None