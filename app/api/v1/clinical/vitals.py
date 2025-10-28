from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.labs_vitals import Vital
from app.models.patient import Patient
from app.schemas.clinical import VitalCreate, VitalUpdate, VitalOut
from .common import ensure_patient_exists

router = APIRouter(prefix="/clinical/vitals", tags=["Clinical - Vitals"])

@router.post("", response_model=VitalOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_vital(payload: VitalCreate, db: AsyncSession = Depends(get_db)):
    await ensure_patient_exists(db, payload.patient_id)
    vt = Vital(**payload.model_dump())
    db.add(vt)
    await db.commit()
    await db.refresh(vt)
    return vt

@router.get("", response_model=list[VitalOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_vitals(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Vital)
        .where(Vital.patient_id == patient_id)
        .order_by(Vital.date.desc())
    )
    return res.scalars().all()

@router.get("/{id}", response_model=VitalOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_vital(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Vital).where(Vital.id == id))
    vt = res.scalar_one_or_none()
    if not vt:
        raise HTTPException(status_code=404, detail="Signo vital no encontrado")
    return vt

@router.patch("/{id}", response_model=VitalOut,
              dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def update_vital(id: str, patch: VitalUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Vital).where(Vital.id == id))
    vt = res.scalar_one_or_none()
    if not vt:
        raise HTTPException(status_code=404, detail="Signo vital no encontrado")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(vt, k, v)
    await db.commit()
    await db.refresh(vt)
    return vt

@router.delete("/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_vital(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Vital).where(Vital.id == id))
    await db.commit()
    return

# ------- “me” --------
@router.get("/patient/me", response_model=list[VitalOut],
            dependencies=[Depends(require_roles(RoleEnum.patient))])
async def my_vitals_patient(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    pat = (await db.execute(select(Patient).where(Patient.user_id == current.id))).scalar_one_or_none()
    if not pat:
        return []
    res = await db.execute(
        select(Vital)
        .where(Vital.patient_id == pat.id)
        .order_by(Vital.date.desc())
        .offset(offset).limit(limit)
    )
    return res.scalars().all()
