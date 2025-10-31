from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.models.links import ClinicPatient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientOut
from app.models.doctor import Doctor
from app.schemas.clinical import VitalOut
from app.models.labs_vitals import Vital 

router = APIRouter(prefix="/patients", tags=["patients"])

async def _get_patient_or_404(id: str, db: AsyncSession) -> Patient:
    q = select(Patient).options(selectinload(Patient.clinics)).where(Patient.id == id)
    res = await db.execute(q)
    pt = res.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return pt

def _can_edit_patient(user: User, pt: Patient) -> bool:
    return user.role == RoleEnum.admin or (user.role == RoleEnum.patient and pt.user_id == user.id)

@router.post("/", response_model=PatientOut, status_code=201, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def create_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    pt = Patient(**payload.model_dump())
    db.add(pt)
    await db.commit()
    # await db.refresh(pt)
    pt = await _get_patient_or_404(pt.id, db)
    return PatientOut.from_model(pt)

@router.get("/", response_model=list[PatientOut], dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def list_patients(
    clinic_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if clinic_id:
        q = (
            select(Patient)
            .join(ClinicPatient).where(ClinicPatient.clinic_id == clinic_id)
            .options(selectinload(Patient.clinics))
        )
    else:
        q = select(Patient).options(selectinload(Patient.clinics))

    res = await db.execute(q.offset(offset).limit(limit))
    pts = res.scalars().unique().all()
    return [PatientOut.from_model(p) for p in pts]

@router.get("/me", response_model=PatientOut, dependencies=[Depends(require_roles(RoleEnum.patient))])
async def get_my_patient(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Patient).where(Patient.user_id == current.id)
    res = await db.execute(q)
    pt = res.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return PatientOut.from_model(pt)


@router.get("/{id}", response_model=PatientOut, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def get_patient(id: str, db: AsyncSession = Depends(get_db)):
    p = await _get_patient_or_404(id, db)
    return PatientOut.from_model(p)


@router.patch("/{id}", response_model=PatientOut)
async def update_patient(id: str, patch: PatientUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await _get_patient_or_404(id, db)
    if not _can_edit_patient(current, p) and current.role not in (RoleEnum.doctor, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Permiso denegado")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    p = await _get_patient_or_404(id, db)
    return PatientOut.from_model(p)

@router.delete("/{id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin))])
async def delete_patient(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicPatient).where(ClinicPatient.patient_id == id))
    await db.execute(delete(Patient).where(Patient.id == id))
    await db.commit()
    return

@router.post("/{id}/clinics/{clinic_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def assign_patient_to_clinic(id: str, clinic_id: str, db: AsyncSession = Depends(get_db)):
    _ = await _get_patient_or_404(id, db)
    res = await db.execute(select(Clinic).where(Clinic.id == clinic_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Clínica no encontrada")
    res2 = await db.execute(select(ClinicPatient).where(ClinicPatient.patient_id == id, ClinicPatient.clinic_id == clinic_id))
    if not res2.scalar_one_or_none():
        db.add(ClinicPatient(patient_id=id, clinic_id=clinic_id))
        await db.commit()
    return

@router.delete("/{id}/clinics/{clinic_id}", status_code=204, dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def unassign_patient_from_clinic(id: str, clinic_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(ClinicPatient).where(ClinicPatient.patient_id == id, ClinicPatient.clinic_id == clinic_id))
    await db.commit()
    return


# --- PACIENTES POR CLÍNICA (ruta explícita, además del query param que ya tenés) ---
@router.get("/clinic/{clinic_id}", response_model=list[PatientOut], dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def list_patients_by_clinic(
    clinic_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Patient)
        .join(ClinicPatient, ClinicPatient.patient_id == Patient.id)
        .where(ClinicPatient.clinic_id == clinic_id)
        .options(selectinload(Patient.clinics))
    )
    res = await db.execute(q.offset(offset).limit(limit))
    pts = res.scalars().unique().all()
    return [PatientOut.from_model(p) for p in pts]


# --- PACIENTES POR DOCTOR (ID explícito) ---
from app.models.links import ClinicDoctor  # asegúrate de tenerlo importado en el header

@router.get("/doctor/{doctor_id}", response_model=list[PatientOut], dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def list_patients_by_doctor(
    doctor_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Patient)
        .join(ClinicPatient, ClinicPatient.patient_id == Patient.id)
        .join(ClinicDoctor, ClinicDoctor.clinic_id == ClinicPatient.clinic_id)
        .where(ClinicDoctor.doctor_id == doctor_id)
        .options(selectinload(Patient.clinics))
    )
    res = await db.execute(q.offset(offset).limit(limit))
    pts = res.scalars().unique().all()
    return [PatientOut.from_model(p) for p in pts]


# --- PACIENTES DEL DOCTOR AUTENTICADO (/patients/doctor/me) ---
@router.get("/doctor/me", response_model=list[PatientOut], dependencies=[Depends(require_roles(RoleEnum.doctor))])
async def list_my_patients_as_doctor(
    current: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Buscar perfil doctor por user_id
    doc = (await db.execute(select(Doctor).where(Doctor.user_id == current.id))).scalar_one_or_none()
    if not doc:
        return []
    q = (
        select(Patient)
        .join(ClinicPatient, ClinicPatient.patient_id == Patient.id)
        .join(ClinicDoctor, ClinicDoctor.clinic_id == ClinicPatient.clinic_id)
        .where(ClinicDoctor.doctor_id == doc.id)
        .options(selectinload(Patient.clinics))
    )
    res = await db.execute(q.offset(offset).limit(limit))
    pts = res.scalars().unique().all()
    return [PatientOut.from_model(p) for p in pts]

@router.get("/{id}/vital_signs", response_model=list[VitalOut], dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_patient_vital_signs(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Obtener el ID del usuario (current_user es el usuario autenticado a partir del token)
    user_id = current_user.id
    
    # Buscar el paciente relacionado con este usuario (el paciente tiene un user_id)
    patient = await db.execute(select(Patient).where(Patient.user_id == user_id))
    patient = patient.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Obtener los signos vitales del paciente
    q = select(Vital).where(Vital.patient_id == patient.id)
    res = await db.execute(q)
    vital_signs = res.scalars().all()
    
    if not vital_signs:
        raise HTTPException(status_code=404, detail="No se encontraron signos vitales para el paciente")
    
    # Devolver los signos vitales como una lista de modelos Pydantic
    return vital_signs
