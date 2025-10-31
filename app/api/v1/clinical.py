from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import RoleEnum, User
from app.models.clinical import Consultation, Medication
from app.models.patient import Patient
from app.models.labs_vitals import LabResult, Vital
from app.schemas.clinical import (
    ConsultationCreate, ConsultationOut, ConsultationUpdate,
    MedicationCreate, MedicationUpdate, MedicationOut,
    LabCreate, LabUpdate, LabOut,
    VitalCreate, VitalUpdate, VitalOut
)

router = APIRouter(prefix="/clinical", tags=["clinical"])

# --- helpers (permisos) ---
async def _ensure_patient_exists(db: AsyncSession, patient_id: str):
    res = await db.execute(select(Patient.id).where(Patient.id == patient_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

def _can_write(user: User) -> bool:
    return user.role in (RoleEnum.admin, RoleEnum.doctor)

def _can_read_own_patient(user: User, patient_id: str) -> bool:
    # si el user es patient, permitir leer solo su propia ficha (si está linkeado)
    # (opcional: hacer join a Patient.user_id para validar exacto)
    return user.role == RoleEnum.patient

# --------- CONSULTATIONS ----------
@router.post("/consultations", response_model=ConsultationOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def create_consultation(payload: ConsultationCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_patient_exists(db, payload.patient_id)
    c = Consultation(**payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c

@router.get("/consultations", response_model=list[ConsultationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def list_consultations(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.patient_id == patient_id)
                           .order_by(Consultation.date.desc()))
    return res.scalars().all()

@router.get("/consultations/{id}", response_model=ConsultationOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_consultation(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.id == id))
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return c

@router.patch("/consultations/{id}", response_model=ConsultationOut,
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

@router.delete("/consultations/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_consultation(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Consultation).where(Consultation.id == id))
    await db.commit()
    return

@router.get("/consultations/by-appointment/{appointment_id}", response_model=list[ConsultationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_by_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Consultation).where(Consultation.appointment_id == appointment_id))
    return res.scalars().all()

# --------- MEDICATIONS -----------
@router.post("/medications", response_model=MedicationOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_medication(payload: MedicationCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_patient_exists(db, payload.patient_id)
    m = Medication(**payload.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m

@router.get("/medications", response_model=list[MedicationOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_medications(patient_id: str = Query(...), current: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    # si es patient, podrías validar que patient_id corresponde a su user_id (extra)
    res = await db.execute(select(Medication).where(Medication.patient_id == patient_id))
    return res.scalars().all()

@router.patch("/medications/{id}", response_model=MedicationOut,
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

@router.delete("/medications/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_medication(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Medication).where(Medication.id == id))
    await db.commit()
    return

# ---------- LAB RESULTS ----------
@router.post("/labs", response_model=LabOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_lab(payload: LabCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_patient_exists(db, payload.patient_id)
    lab = LabResult(**payload.model_dump())
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return lab

@router.get("/labs", response_model=list[LabOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_labs(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(LabResult).where(LabResult.patient_id == patient_id).order_by(LabResult.date.desc())
    )
    return res.scalars().all()

@router.get("/labs/{id}", response_model=LabOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_lab(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(LabResult).where(LabResult.id == id))
    lab = res.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Laboratorio no encontrado")
    return lab

@router.patch("/labs/{id}", response_model=LabOut,
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

@router.delete("/labs/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_lab(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(LabResult).where(LabResult.id == id))
    await db.commit()
    return

# ---------- VITALS ----------
@router.post("/vitals", response_model=VitalOut, status_code=201,
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def add_vital(payload: VitalCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_patient_exists(db, payload.patient_id)
    vt = Vital(**payload.model_dump())
    db.add(vt)
    await db.commit()
    await db.refresh(vt)
    return vt

@router.get("/vitals", response_model=list[VitalOut],
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def list_vitals(patient_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Vital).where(Vital.patient_id == patient_id).order_by(Vital.date.desc())
    )
    return res.scalars().all()

@router.get("/vitals/{id}", response_model=VitalOut,
            dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def get_vital(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Vital).where(Vital.id == id))
    vt = res.scalar_one_or_none()
    if not vt:
        raise HTTPException(status_code=404, detail="Signo vital no encontrado")
    return vt

@router.patch("/vitals/{id}", response_model=VitalOut,
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

@router.delete("/vitals/{id}", status_code=204,
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_vital(id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Vital).where(Vital.id == id))
    await db.commit()
    return
