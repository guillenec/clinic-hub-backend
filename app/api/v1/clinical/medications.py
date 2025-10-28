from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.clinical import Medication
from app.models.patient import Patient
from app.schemas.clinical import MedicationCreate, MedicationUpdate, MedicationOut
from .common import ensure_patient_exists

router = APIRouter(prefix="/clinical/medications", tags=["Clinical - Medications"])

@router.post("", response_model=MedicationOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_medication(payload: MedicationCreate, db: AsyncSession = Depends(get_db)):
    await ensure_patient_exists(db, payload.patient_id)
    m = Medication(**payload.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m

@router.get("", response_model=list[MedicationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_medications(
    patient_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Medication).where(Medication.patient_id == patient_id))
    return res.scalars().all()

@router.patch("/{id}", response_model=MedicationOut,
              dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def update_medication(id: str, patch: MedicationUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Medication).where(Medication.id == id))
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Medicación no encontrada")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    await db.commit()
    await db.refresh(m)
    return m

@router.delete("/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_medication(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Medication).where(Medication.id == id))
    await db.commit()
    return

# ------- “me” para el front --------

@router.get("/patient/me", response_model=list[MedicationOut],
            dependencies=[Depends(require_roles(RoleEnum.patient))])
async def my_medications_patient(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    pat = (await db.execute(select(Patient).where(Patient.user_id == current.id))).scalar_one_or_none()
    if not pat:
        return []
    res = await db.execute(
        select(Medication)
        .where(Medication.patient_id == pat.id)
        .offset(offset).limit(limit)
    )
    return res.scalars().all()
