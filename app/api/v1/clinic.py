from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.links import ClinicDoctor, ClinicPatient  # <- ajusta si el nombre difiere
from app.schemas.clinic import ClinicCreate, ClinicOut, ClinicUpdate

router = APIRouter(prefix="/clinics", tags=["clinics"])


# ---------- helpers ----------
async def _get_clinic_or_404(id: str, db: AsyncSession) -> Clinic:
    q = select(Clinic).where(Clinic.id == id)
    c = (await db.execute(q)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")
    return c

# ---------- endpoints ----------

# ---------- create ----------
@router.post("/", response_model=ClinicOut, status_code=201, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def create_clinic(payload: ClinicCreate, db: AsyncSession = Depends(get_db)):
    clinic = Clinic(**payload.model_dump())
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic

# ---------- list ----------
@router.get("/", response_model=list[ClinicOut])
async def list_clinics(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = (
        select(Clinic)
        .options(selectinload(Clinic.doctors), selectinload(Clinic.patients))
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return rows

@router.get("/{id}", response_model=ClinicOut)
async def get_clinic(id: str, db: AsyncSession = Depends(get_db)):
    q = select(Clinic).options(
        selectinload(Clinic.doctors), selectinload(Clinic.patients)
    ).where(Clinic.id == id)
    c = (await db.execute(q)).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")
    return c

# ---------- filtros útiles ----------
# 1) Clínicas por DOCTOR (ID explícito)
@router.get("/doctor/{doctor_id}", response_model=list[ClinicOut])
async def list_by_doctor(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = (
        select(Clinic)
        .join(ClinicDoctor, ClinicDoctor.clinic_id == Clinic.id)
        .where(ClinicDoctor.doctor_id == doctor_id)
        .options(selectinload(Clinic.doctors), selectinload(Clinic.patients))
        # .order_by(Clinic.created_at.desc())  # <- quitar si no existe
        # .order_by(Clinic.name.asc())
        # .order_by(Clinic.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return rows


# 2) Clínicas por PACIENTE (ID explícito)
@router.get("/patient/{patient_id}", response_model=list[ClinicOut])
async def list_by_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    q = (
        select(Clinic)
        .join(ClinicPatient, ClinicPatient.clinic_id == Clinic.id)
        .where(ClinicPatient.patient_id == patient_id)
        .options(selectinload(Clinic.doctors), selectinload(Clinic.patients))
        # .order_by(Clinic.created_at.desc())  # <- quitar si no existe
        # .order_by(Clinic.name.asc())
        # .order_by(Clinic.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return rows

# 3) Clínicas del DOCTOR autenticado (/clinics/doctor/me)
@router.get("/doctor/me", response_model=list[ClinicOut])
async def list_my_clinics_as_doctor(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    # buscar el doctor por user_id
    doc = (await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))).scalar_one_or_none()
    if not doc:
        return []
    q = (
        select(Clinic)
        .join(ClinicDoctor, ClinicDoctor.clinic_id == Clinic.id)
        .where(ClinicDoctor.doctor_id == doc.id)
        .options(selectinload(Clinic.doctors), selectinload(Clinic.patients))
    )
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()
    return rows

# 4) Clínicas del PACIENTE autenticado (/clinics/patient/me)
@router.get("/patient/me", response_model=list[ClinicOut])
async def list_my_clinics_as_patient(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    pat = (await db.execute(select(Patient).where(Patient.user_id == current_user.id))).scalar_one_or_none()
    if not pat:
        return []
    q = (
        select(Clinic)
        .join(ClinicPatient, ClinicPatient.clinic_id == Clinic.id)
        .where(ClinicPatient.patient_id == pat.id)
        .options(selectinload(Clinic.doctors), selectinload(Clinic.patients))
    )
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()
    return rows

# ---------- update ----------
@router.put("/{id}", response_model=ClinicOut, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def replace_clinic(
    id: str,
    payload: ClinicCreate,                 # reemplazo total: exige todos los campos
    db: AsyncSession = Depends(get_db),
):
    clinic = (await db.execute(select(Clinic).where(Clinic.id == id))).scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")

    data = payload.model_dump()
    for k, v in data.items():
        setattr(clinic, k, v)

    await db.flush()
    await db.commit()
    await db.refresh(clinic)
    return clinic


@router.patch("/{id}", response_model=ClinicOut, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def update_clinic(
    id: str,
    payload: ClinicUpdate,                 # actualización parcial
    db: AsyncSession = Depends(get_db),
):
    clinic = (await db.execute(select(Clinic).where(Clinic.id == id))).scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")

    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(clinic, k, v)

    await db.flush()
    await db.commit()
    await db.refresh(clinic)
    return clinic

# ---------- delete ----------
@router.delete("/{id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_clinic(id: str, db: AsyncSession = Depends(get_db)):
    clinic = (await db.execute(select(Clinic).where(Clinic.id == id))).scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clínica no encontrada")

    await db.delete(clinic)
    await db.commit()

# ---------- asignaciones ----------
@router.post("/{id}/doctors/{doctor_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def assign_doctor_to_clinic(id: str, doctor_id: str, db: AsyncSession = Depends(get_db)):
    _ = await _get_clinic_or_404(id, db)
    doc = (await db.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")
    exists = (await db.execute(
        select(ClinicDoctor).where(ClinicDoctor.clinic_id == id, ClinicDoctor.doctor_id == doctor_id)
    )).scalar_one_or_none()
    if not exists:
        db.add(ClinicDoctor(clinic_id=id, doctor_id=doctor_id))
        await db.commit()
    return

@router.delete("/{id}/doctors/{doctor_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def unassign_doctor_from_clinic(id: str, doctor_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicDoctor).where(ClinicDoctor.clinic_id == id, ClinicDoctor.doctor_id == doctor_id))
    await db.commit()
    return

@router.post("/{id}/patients/{patient_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def assign_patient_to_clinic(id: str, patient_id: str, db: AsyncSession = Depends(get_db)):
    _ = await _get_clinic_or_404(id, db)
    pat = (await db.execute(select(Patient).where(Patient.id == patient_id))).scalar_one_or_none()
    if not pat:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    exists = (await db.execute(
        select(ClinicPatient).where(ClinicPatient.clinic_id == id, ClinicPatient.patient_id == patient_id)
    )).scalar_one_or_none()
    if not exists:
        db.add(ClinicPatient(clinic_id=id, patient_id=patient_id))
        await db.commit()
    return


@router.delete("/{id}/patients/{patient_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def unassign_patient_from_clinic(id: str, patient_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicPatient).where(ClinicPatient.clinic_id == id, ClinicPatient.patient_id == patient_id))
    await db.commit()
    return