from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.db import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentOut
from app.models.links import ClinicDoctor, ClinicPatient


router = APIRouter(prefix="/appointments", tags=["appointments"])

# ---------- helpers ----------
async def _get_doctor_id_for_user(user: User, db: AsyncSession) -> str | None:
    if user.role != RoleEnum.doctor:
        return None
    res = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    return res.scalar_one_or_none()

async def _get_patient_id_for_user(user: User, db: AsyncSession) -> str | None:
    if user.role != RoleEnum.patient:
        return None
    res = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
    return res.scalar_one_or_none()

async def _get_appt_or_404(id: str, db: AsyncSession) -> Appointment:
    q = select(Appointment).options(
        selectinload(Appointment.doctor),
        selectinload(Appointment.patient),
        selectinload(Appointment.clinic),
    ).where(Appointment.id == id)
    res = await db.execute(q)
    ap = res.scalar_one_or_none()
    if not ap:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return ap

def _can_view(user: User, ap: Appointment, my_doctor_id: str | None, my_patient_id: str | None) -> bool:
    if user.role == RoleEnum.admin:
        return True
    if user.role == RoleEnum.doctor and my_doctor_id and ap.doctor_id == my_doctor_id:
        return True
    if user.role == RoleEnum.patient and my_patient_id and ap.patient_id == my_patient_id:
        return True
    return False

def _can_edit(user: User, ap: Appointment, my_doctor_id: str | None) -> bool:
    # editar/cancelar: admin o el doctor dueño
    return user.role == RoleEnum.admin or (user.role == RoleEnum.doctor and my_doctor_id == ap.doctor_id)

def _validate_times(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="ends_at debe ser posterior a starts_at")

async def _exists_or_404(db: AsyncSession, model, id: str, what: str):
    res = await db.execute(select(model).where(model.id == id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"{what} no encontrado")

# ---------- create ----------
@router.post("/", response_model=AppointmentOut, status_code=201, dependencies=[Depends(get_current_user)])
async def create_appointment(
    payload: AppointmentCreate,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # doctor_id: si el creador es doctor y no lo envió, usamos su perfil
    doctor_id = payload.doctor_id
    # si el usuario actual es doctor, usamos su perfil
    if current.role == RoleEnum.doctor:
        my_doc = await _get_doctor_id_for_user(current, db)
        if not my_doc:
            raise HTTPException(status_code=400, detail="No hay perfil doctor vinculado a este usuario")
        doctor_id = doctor_id or my_doc  # 👈 si viene None, usa el del perfil doctor

    # si sigue sin haber doctor_id (ni payload ni perfil)
    if not doctor_id:
        if current.role != RoleEnum.admin:
            raise HTTPException(status_code=400, detail="Falta doctor_id")
        # si es admin y tampoco lo mandó
        raise HTTPException(status_code=400, detail="Falta doctor_id")

    _validate_times(payload.starts_at, payload.ends_at)

    # validaciones de existencia
    await _exists_or_404(db, Doctor, doctor_id, "Doctor")
    await _exists_or_404(db, Patient, payload.patient_id, "Paciente")
    await _exists_or_404(db, Clinic, payload.clinic_id, "Clínica")

    # doctor ∈ clínica
    res = await db.execute(
        select(ClinicDoctor.doctor_id).where(
            ClinicDoctor.doctor_id == doctor_id,
            ClinicDoctor.clinic_id == payload.clinic_id,
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El doctor no pertenece a la clínica")

    # (opcional) paciente ∈ clínica
    res = await db.execute(
        select(ClinicPatient.patient_id).where(
            ClinicPatient.patient_id == payload.patient_id,
            ClinicPatient.clinic_id == payload.clinic_id,
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El paciente no pertenece a la clínica")

    # --- evitar solapamientos del mismo doctor en la misma clínica ---
    
    overlap_q = select(Appointment.id).where(
        Appointment.doctor_id == doctor_id,
        Appointment.clinic_id == payload.clinic_id,
        Appointment.starts_at < payload.ends_at, # empieza antes de que termine el nuevo
        Appointment.ends_at   > payload.starts_at, # termina después de que empieza el nuevo
        Appointment.status != "cancelled",   # opcional: ignorar cancelados
    )
    res = await db.execute(overlap_q)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ya existe un turno para este doctor que se solapa con el horario solicitado"
        )
    
    ap = Appointment(
        doctor_id=doctor_id,
        patient_id=payload.patient_id,
        clinic_id=payload.clinic_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        type=payload.type,      # type: ignore[arg-type]
        status=payload.status,  # type: ignore[arg-type]
    )
    db.add(ap)
    await db.commit()
    await db.refresh(ap)
    return ap  # from_attributes=True en schema

# ---------- list ----------
@router.get("/", response_model=list[AppointmentOut], dependencies=[Depends(get_current_user)])
async def list_appointments(
    date_from: datetime | None = Query(None),
    date_to:   datetime | None = Query(None),
    clinic_id: str | None = Query(None),
    status:    str | None = Query(None),
    limit:     int = Query(50, ge=1, le=200),
    offset:    int = Query(0, ge=0),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    my_doc_id = await _get_doctor_id_for_user(current, db)
    my_pt_id  = await _get_patient_id_for_user(current, db)

    q = select(Appointment).options(
        selectinload(Appointment.doctor),
        selectinload(Appointment.patient),
        selectinload(Appointment.clinic),
    )

    # alcance por rol
    if current.role == RoleEnum.doctor and my_doc_id:
        q = q.where(Appointment.doctor_id == my_doc_id)
    elif current.role == RoleEnum.patient and my_pt_id:
        q = q.where(Appointment.patient_id == my_pt_id)
    # admin ve todo

    # filtros
    if clinic_id:
        q = q.where(Appointment.clinic_id == clinic_id)
    if date_from:
        q = q.where(Appointment.starts_at >= date_from)
    if date_to:
        q = q.where(Appointment.starts_at < date_to)
    if status in {"pending", "confirmed", "cancelled"}:
        q = q.where(Appointment.status == status)  # type: ignore[arg-type]

    # res = await db.execute(q.order_by(Appointment.starts_at))
    # return res.scalars().all()
    res = await db.execute(q.order_by(Appointment.starts_at).offset(offset).limit(limit))
    return res.scalars().all()

# atajos cómodos
@router.get("/doctor/me", response_model=list[AppointmentOut], dependencies=[Depends(require_roles(RoleEnum.doctor))])
async def my_doctor_appointments(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    my_doc_id = await _get_doctor_id_for_user(current, db)
    if not my_doc_id:
        return []
    res = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.clinic))
        .where(Appointment.doctor_id == my_doc_id)
        .order_by(Appointment.starts_at)
    )
    return res.scalars().all()

@router.get("/patient/me", response_model=list[AppointmentOut], dependencies=[Depends(require_roles(RoleEnum.patient))])
async def my_patient_appointments(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    my_pt_id = await _get_patient_id_for_user(current, db)
    if not my_pt_id:
        return []
    res = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor), selectinload(Appointment.clinic))
        .where(Appointment.patient_id == my_pt_id)
        .order_by(Appointment.starts_at)
    )
    return res.scalars().all()

# ---------- get ----------
@router.get("/{id}", response_model=AppointmentOut, dependencies=[Depends(get_current_user)])
async def get_appointment(id: str, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ap = await _get_appt_or_404(id, db)
    my_doc_id = await _get_doctor_id_for_user(current, db)
    my_pt_id  = await _get_patient_id_for_user(current, db)
    if not _can_view(current, ap, my_doc_id, my_pt_id):
        raise HTTPException(status_code=403, detail="Permiso denegado")
    return ap

# ---------- update ----------
@router.patch("/{id}", response_model=AppointmentOut, dependencies=[Depends(get_current_user)])
async def update_appointment(id: str, patch: AppointmentUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ap = await _get_appt_or_404(id, db)
    my_doc_id = await _get_doctor_id_for_user(current, db)
    if not _can_edit(current, ap, my_doc_id):
        raise HTTPException(status_code=403, detail="Permiso denegado")

    data = patch.model_dump(exclude_unset=True)

    if "starts_at" in data or "ends_at" in data or "doctor_id" in data or "clinic_id" in data:
        new_starts = data.get("starts_at", ap.starts_at)
        new_ends   = data.get("ends_at",   ap.ends_at)
        # si permiten cambiar doctor/clinica en PATCH (p.ej. admin)
        eff_doctor_id = data.get("doctor_id", ap.doctor_id)
        eff_clinic_id = data.get("clinic_id", ap.clinic_id)

        _validate_times(new_starts, new_ends)

        # evitar solapamiento con otros turnos del mismo doctor en la misma clínica
        overlap_q = select(Appointment.id).where(
            Appointment.doctor_id == eff_doctor_id,
            Appointment.clinic_id == eff_clinic_id,
            Appointment.id != ap.id,            # excluir el propio
            Appointment.starts_at < new_ends,
            Appointment.ends_at   > new_starts,
            Appointment.status != "cancelled",  # opcional: ignorar cancelados
        )
        res = await db.execute(overlap_q)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="El nuevo horario se solapa con otro turno del doctor en esa clínica"
            )

    for k, v in data.items():
        setattr(ap, k, v)
    await db.commit()
    await db.refresh(ap)
    return ap

# ---------- delete ----------
@router.delete("/{id}", status_code=204, dependencies=[Depends(get_current_user)])
async def delete_appointment(id: str, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ap = await _get_appt_or_404(id, db)
    my_doc_id = await _get_doctor_id_for_user(current, db)
    if not _can_edit(current, ap, my_doc_id):
        raise HTTPException(status_code=403, detail="Permiso denegado")

    await db.execute(delete(Appointment).where(Appointment.id == id))
    await db.commit()
    return
