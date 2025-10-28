from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.patient import Patient
from app.models.user import User, RoleEnum

async def ensure_patient_exists(db: AsyncSession, patient_id: str):
    res = await db.execute(select(Patient.id).where(Patient.id == patient_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

def can_write(user: User) -> bool:
    return user.role in (RoleEnum.admin, RoleEnum.doctor)

def is_patient(user: User) -> bool:
    return user.role == RoleEnum.patient
