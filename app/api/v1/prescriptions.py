from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date
import uuid

from app.core.db import get_db
from app.core.security import get_current_user   # 👈 trae el usuario del token
from app.schemas.prescription import (
    PrescriptionCreate, PrescriptionOut, PrescriptionUpdate
)
from app.models.prescription import Prescription, PrescriptionItem
from app.models.doctor import Doctor
from app.models.user import User
from app.models.patient import Patient
from ._helpers import gen_code

router = APIRouter(prefix="/clinical/prescriptions", tags=["Clinical - Prescriptions"])

# ---------- helpers ----------
async def _doctor_snapshot(db: AsyncSession, doctor_id: str) -> dict:
    doc = (await db.execute(select(Doctor).where(Doctor.id == doctor_id))).scalar_one_or_none()
    if not doc:
        return {}
    return {
        "id": doc.id,
        "name": doc.name,
        "license": getattr(doc, "license", None),
        "signature_png": getattr(doc, "signature_png", None),
        "stamp_png": getattr(doc, "stamp_png", None),
        "specialty": getattr(doc, "specialty", None),
    }

async def _get_current_doctor_id(db: AsyncSession, user: User) -> Optional[str]:
    q = select(Doctor.id).where(Doctor.user_id == user.id)
    return (await db.execute(q)).scalar_one_or_none()

# ---------- create (igual que ya tienes) ----------
@router.post("", response_model=PrescriptionOut)
async def create_prescription(payload: PrescriptionCreate, db: AsyncSession = Depends(get_db)):
    rx = Prescription(
        id=str(uuid.uuid4()),
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        issued_date=payload.issued_date or date.today(),
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        include_signature=payload.include_signature,
        include_stamp=payload.include_stamp,
        verify_code=gen_code(8),
    )
    for idx, it in enumerate(payload.items):
        rx.items.append(PrescriptionItem(
            position=idx, drug=it.drug, dose=it.dose,
            frequency=it.frequency, duration=it.duration, notes=it.notes
        ))
    db.add(rx)
    await db.flush()
    await db.commit()
    await db.refresh(rx, attribute_names=["items"])

    out = PrescriptionOut.model_validate(rx, from_attributes=True)
    out.doctor = await _doctor_snapshot(db, rx.doctor_id)
    return out

# ---------- list con filtros (ya lo tienes) ----------
@router.get("", response_model=List[PrescriptionOut])
async def list_prescriptions(
    db: AsyncSession = Depends(get_db),
    patient_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = (
        select(Prescription)
        .options(selectinload(Prescription.items))
        .order_by(Prescription.created_at.desc())
    )
    if patient_id:
        q = q.where(Prescription.patient_id == patient_id)
    if doctor_id:
        q = q.where(Prescription.doctor_id == doctor_id)

    rows = list((await db.execute(q.offset(offset).limit(limit))).scalars().unique())
    out: List[PrescriptionOut] = []
    for rx in rows:
        dto = PrescriptionOut.model_validate(rx, from_attributes=True)
        dto.doctor = await _doctor_snapshot(db, rx.doctor_id)
        out.append(dto)
    return out

# ---------- “me” (por médico autenticado) ----------
@router.get("/doctor/me", response_model=List[PrescriptionOut])
async def list_my_prescriptions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    doctor_id = await _get_current_doctor_id(db, user)
    if not doctor_id:
        raise HTTPException(status_code=403, detail="No asociado a un doctor")

    q = (
        select(Prescription)
        .options(selectinload(Prescription.items))
        .where(Prescription.doctor_id == doctor_id)
        .order_by(Prescription.created_at.desc())
        .offset(offset).limit(limit)
    )
    rows = list((await db.execute(q)).scalars().unique())
    out: List[PrescriptionOut] = []
    for rx in rows:
        dto = PrescriptionOut.model_validate(rx, from_attributes=True)
        dto.doctor = await _doctor_snapshot(db, rx.doctor_id)
        out.append(dto)
    return out

@router.get("/patient/me", response_model=List[PrescriptionOut])
async def list_by_patient_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Buscar el paciente del usuario autenticado
    pat = (await db.execute(select(Patient).where(Patient.user_id == current_user.id))).scalar_one_or_none()
    if not pat:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    q = (
        select(Prescription)
        .options(selectinload(Prescription.items))
        .where(Prescription.patient_id == pat.id)
        .order_by(Prescription.created_at.desc())
        .offset(offset).limit(limit)
    )

    rows = list((await db.execute(q)).scalars().unique())

    out: List[PrescriptionOut] = []
    for rx in rows:
        dto = PrescriptionOut.model_validate(rx, from_attributes=True)
        dto.doctor = await _doctor_snapshot(db, rx.doctor_id)
        out.append(dto)
    return out

# ---------- azúcar por paciente ----------
@router.get("/patient/{patient_id}", response_model=List[PrescriptionOut])
async def list_by_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = (
        select(Prescription)
        .options(selectinload(Prescription.items))
        .where(Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
        .offset(offset).limit(limit)
    )
    rows = list((await db.execute(q)).scalars().unique())
    out: list[PrescriptionOut] = []
    for rx in rows:
        dto = PrescriptionOut.model_validate(rx, from_attributes=True)
        dto.doctor = await _doctor_snapshot(db, rx.doctor_id)
        out.append(dto)
    return out

# ---------- get by id (como ya lo tienes) ----------
@router.get("/{rx_id}", response_model=PrescriptionOut)
async def get_prescription(rx_id: str, db: AsyncSession = Depends(get_db)):
    q = select(Prescription).options(selectinload(Prescription.items)).where(Prescription.id == rx_id)
    rx = (await db.execute(q)).scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    out = PrescriptionOut.model_validate(rx, from_attributes=True)
    out.doctor = await _doctor_snapshot(db, rx.doctor_id)
    return out

# ---------- PUT (update completo) ----------
@router.put("/{rx_id}", response_model=PrescriptionOut)
async def replace_prescription(rx_id: str, body: PrescriptionCreate, db: AsyncSession = Depends(get_db)):
    q = select(Prescription).options(selectinload(Prescription.items)).where(Prescription.id == rx_id)
    rx = (await db.execute(q)).scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    rx.patient_id = body.patient_id
    rx.doctor_id = body.doctor_id
    rx.issued_date = body.issued_date
    rx.diagnosis = body.diagnosis
    rx.notes = body.notes
    rx.include_signature = body.include_signature
    rx.include_stamp = body.include_stamp

    # reemplazo total de items
    rx.items.clear()
    for idx, it in enumerate(body.items):
        rx.items.append(PrescriptionItem(
            position=idx, drug=it.drug, dose=it.dose,
            frequency=it.frequency, duration=it.duration, notes=it.notes
        ))

    await db.flush()
    await db.commit()
    await db.refresh(rx, attribute_names=["items"])

    out = PrescriptionOut.model_validate(rx, from_attributes=True)
    out.doctor = await _doctor_snapshot(db, rx.doctor_id)
    return out

# ---------- PATCH (parcial) ----------
@router.patch("/{rx_id}", response_model=PrescriptionOut)
async def update_prescription(rx_id: str, patch: PrescriptionUpdate, db: AsyncSession = Depends(get_db)):
    q = select(Prescription).options(selectinload(Prescription.items)).where(Prescription.id == rx_id)
    rx = (await db.execute(q)).scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if patch.issued_date is not None: rx.issued_date = patch.issued_date
    if patch.diagnosis   is not None: rx.diagnosis   = patch.diagnosis
    if patch.notes       is not None: rx.notes       = patch.notes
    if patch.include_signature is not None: rx.include_signature = patch.include_signature
    if patch.include_stamp     is not None: rx.include_stamp     = patch.include_stamp

    if patch.items is not None:
        existing_by_id = {it.id: it for it in rx.items}
        for it_patch in patch.items:
            if it_patch.id and it_patch.id in existing_by_id:
                it = existing_by_id[it_patch.id]
                if it_patch.position  is not None: it.position  = it_patch.position
                if it_patch.drug      is not None: it.drug      = it_patch.drug
                if it_patch.dose      is not None: it.dose      = it_patch.dose
                if it_patch.frequency is not None: it.frequency = it_patch.frequency
                if it_patch.duration  is not None: it.duration  = it_patch.duration
                if it_patch.notes     is not None: it.notes     = it_patch.notes
            else:
                # crear nuevo al final
                rx.items.append(PrescriptionItem(
                    position=(it_patch.position if it_patch.position is not None
                              else (max([i.position for i in rx.items], default=-1) + 1)),
                    drug=it_patch.drug or "",
                    dose=it_patch.dose or "",
                    frequency=it_patch.frequency or "",
                    duration=it_patch.duration or "",
                    notes=it_patch.notes,
                ))

    await db.flush()
    await db.commit()
    await db.refresh(rx, attribute_names=["items"])

    out = PrescriptionOut.model_validate(rx, from_attributes=True)
    out.doctor = await _doctor_snapshot(db, rx.doctor_id)
    return out

# ---------- delete ----------
@router.delete("/{rx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(rx_id: str, db: AsyncSession = Depends(get_db)):
    rx = (await db.execute(select(Prescription).where(Prescription.id == rx_id))).scalar_one_or_none()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    await db.delete(rx)
    await db.commit()
