from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.clinical import Consultation
from app.models.patient import Patient
from app.schemas.clinical import (
    ConsultationCreate, ConsultationOut, ConsultationUpdate,
)
from .common import ensure_patient_exists

router = APIRouter(prefix="/clinical/consultations", tags=["Clinical - Consultations"])

# CREATE
@router.post("", response_model=ConsultationOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def create_consultation(payload: ConsultationCreate, db: AsyncSession = Depends(get_db)):
    await ensure_patient_exists(db, payload.patient_id)
    c = Consultation(**payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

# LIST (por patient_id)
@router.get("", response_model=list[ConsultationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def list_consultations(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Consultation)
        .where(Consultation.patient_id == patient_id)
        .order_by(Consultation.date.desc())
    )
    return res.scalars().all()

# GET by id
@router.get("/{id}", response_model=ConsultationOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_consultation(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.id == id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return c

# PATCH
@router.patch("/{id}", response_model=ConsultationOut,
              dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def update_consultation(id: str, patch: ConsultationUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.id == id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")

    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(c, k, v)

    await db.commit()
    await db.refresh(c)
    return c

# DELETE
@router.delete("/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_consultation(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Consultation).where(Consultation.id == id))
    await db.commit()
    return

# by appointment
@router.get("/by-appointment/{appointment_id}", response_model=list[ConsultationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_by_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.appointment_id == appointment_id))
    return res.scalars().all()

# ------- “me” helpers para el front --------

# del paciente autenticado
@router.get("/patient/me", response_model=list[ConsultationOut],
            dependencies=[Depends(require_roles(RoleEnum.patient))])
async def my_consultations_patient(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    # mapear user -> patient
    pat = (await db.execute(select(Patient).where(Patient.user_id == current.id))).scalar_one_or_none()
    if not pat:
        return []
    res = await db.execute(
        select(Consultation)
        .where(Consultation.patient_id == pat.id)
        .order_by(Consultation.date.desc())
        .offset(offset).limit(limit)
    )
    return res.scalars().all()


