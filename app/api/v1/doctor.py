from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.models.links import ClinicDoctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorOut

router = APIRouter(prefix="/doctors", tags=["doctors"])

async def _get_doctor_or_404(id: str, db: AsyncSession) -> Doctor:
    q = select(Doctor).options(selectinload(Doctor.clinics)).where(Doctor.id == id)
    res = await db.execute(q)
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")
    return d

def _can_edit_doctor(user: User, doc: Doctor) -> bool:
    return user.role == RoleEnum.admin or (user.role == RoleEnum.doctor and doc.user_id == user.id)

@router.post("/", response_model=DoctorOut, status_code=201, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def create_doctor(payload: DoctorCreate, db: AsyncSession = Depends(get_db)):
    d = Doctor(**payload.model_dump())
    db.add(d)
    await db.commit()
    # recargar con relaciones
    d = await _get_doctor_or_404(d.id, db)
    return DoctorOut.from_model(d)

@router.get("/", response_model=list[DoctorOut])
async def list_doctors(
    clinic_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Doctor).options(selectinload(Doctor.clinics))
    if clinic_id:
        q = q.join(ClinicDoctor).where(ClinicDoctor.clinic_id == clinic_id)
        
    res = await db.execute(q.offset(offset).limit(limit))
    docs = res.scalars().unique().all()
    return [DoctorOut.from_model(d) for d in docs]

@router.get("/me", response_model=DoctorOut, dependencies=[Depends(require_roles(RoleEnum.doctor))])
async def my_doctor_profile(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Doctor).options(selectinload(Doctor.clinics)).where(Doctor.user_id == current.id)
    res = await db.execute(q)
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="No hay perfil Doctor vinculado")
    return DoctorOut.from_model(d)

@router.get("/{id}", response_model=DoctorOut)
async def get_doctor(id: str, db: AsyncSession = Depends(get_db)):
    d = await _get_doctor_or_404(id, db)
    return DoctorOut.from_model(d)

@router.patch("/{id}", response_model=DoctorOut)
async def update_doctor(
    id: str,
    patch: DoctorUpdate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    d = await _get_doctor_or_404(id, db)
    if not _can_edit_doctor(current, d):
        raise HTTPException(status_code=403, detail="Permiso denegado")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    await db.commit()
    d = await _get_doctor_or_404(id, db)
    return DoctorOut.from_model(d)

@router.delete("/{id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def delete_doctor(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicDoctor).where(ClinicDoctor.doctor_id == id))
    await db.execute(delete(Doctor).where(Doctor.id == id))
    await db.commit()
    return

@router.post("/{id}/clinics/{clinic_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def assign_doctor_to_clinic(id: str, clinic_id: str, db: AsyncSession = Depends(get_db)):
    _ = await _get_doctor_or_404(id, db)
    res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = res.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")
    res2 = await db.execute(select(ClinicDoctor).where(ClinicDoctor.doctor_id == id, ClinicDoctor.clinic_id == clinic_id))
    if not res2.scalar_one_or_none():
        db.add(ClinicDoctor(doctor_id=id, clinic_id=clinic_id))
        await db.commit()
    return

@router.delete("/{id}/clinics/{clinic_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def unassign_doctor_from_clinic(id: str, clinic_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicDoctor).where(ClinicDoctor.doctor_id == id, ClinicDoctor.clinic_id == clinic_id))
    await db.commit()
    return
