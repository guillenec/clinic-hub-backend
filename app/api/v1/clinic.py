from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.db import get_db
from app.models.clinic import Clinic
from app.schemas.clinic import ClinicCreate, ClinicOut

router = APIRouter(prefix="/clinics", tags=["clinics"])

@router.post("/", response_model=ClinicOut, status_code=201)
async def create_clinic(payload: ClinicCreate, db: AsyncSession = Depends(get_db)):
    clinic = Clinic(**payload.model_dump())
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic

@router.get("/", response_model=list[ClinicOut])
async def list_clinics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clinic))
    return res.scalars().all()

@router.get("/{id}", response_model=ClinicOut)
async def get_clinic(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Clinic).where(Clinic.id == id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")
    return c
