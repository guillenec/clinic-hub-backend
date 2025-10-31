from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.labs_vitals import LabResult
from app.models.patient import Patient
from app.schemas.clinical import LabCreate, LabUpdate, LabOut
from .common import ensure_patient_exists

router = APIRouter(prefix="/clinical/labs", tags=["Clinical - Labs"])

@router.post("", response_model=LabOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_lab(payload: LabCreate, db: AsyncSession = Depends(get_db)):
    await ensure_patient_exists(db, payload.patient_id)
    lab = LabResult(**payload.model_dump())
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return lab

@router.get("", response_model=list[LabOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_labs(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(LabResult)
        .where(LabResult.patient_id == patient_id)
        .order_by(LabResult.date.desc())
    )
    return res.scalars().all()

@router.get("/{id}", response_model=LabOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_lab(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(LabResult).where(LabResult.id == id))
    lab = res.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
    return lab

@router.patch("/{id}", response_model=LabOut,
              dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def update_lab(id: str, patch: LabUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(LabResult).where(LabResult.id == id))
    lab = res.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(lab, k, v)
    await db.commit()
    await db.refresh(lab)
    return lab

@router.delete("/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_lab(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(LabResult).where(LabResult.id == id))
    await db.commit()
    return

# ------- “me” --------
@router.get("/patient/me", response_model=list[LabOut],
            dependencies=[Depends(require_roles(RoleEnum.patient))])
async def my_labs_patient(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    pat = (await db.execute(select(Patient).where(Patient.user_id == current.id))).scalar_one_or_none()
    if not pat:
        return []
    res = await db.execute(
        select(LabResult)
        .where(LabResult.patient_id == pat.id)
        .order_by(LabResult.date.desc())
        .offset(offset).limit(limit)
    )
    return res.scalars().all()
