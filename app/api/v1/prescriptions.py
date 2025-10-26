from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.api.deps import require_roles, get_current_user
from app.models.user import RoleEnum, User
from app.models.doctor import Doctor
from app.models.patient import Patient

from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionOut,
    PrescriptionItemIn,
    DoctorAsset,
    PatientMini,
)

router = APIRouter(prefix="/clinical/prescriptions", tags=["clinical"])


@router.post("", response_model=PrescriptionOut, dependencies=[Depends(require_roles(RoleEnum.doctor, RoleEnum.admin))])
async def create_prescription(
    body: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # --- Doctor ---
    res = await db.execute(select(Doctor).where(Doctor.id == body.doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    # --- Paciente ---
    res = await db.execute(select(Patient).where(Patient.id == body.patient_id))
    pat = res.scalar_one_or_none()
    if not pat:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # --- Armado de payload de salida ---
    out = PrescriptionOut(
        id=uuid4().hex,  # TODO: reemplazar por ID de DB cuando lo persistas
        issued_date=body.issued_date,
        created_at=datetime.utcnow(),
        patient=PatientMini(id=pat.id, name=pat.name, dni=getattr(pat, "dni", None)),
        doctor=DoctorAsset(
            id=doc.id,
            name=doc.name,
            license=doc.license,
            signature_png=doc.signature_png if body.include_signature else None,
            stamp_png=doc.stamp_png if body.include_stamp else None,
        ),
        items=[PrescriptionItemIn(**i.model_dump()) for i in body.items],
        diagnosis=body.diagnosis,
        notes=body.notes,
        include_signature=body.include_signature,
        include_stamp=body.include_stamp,
        render={
            "header": {"title": "Receta médica"},
            "footer": {"disclaimer": "Uso responsable de medicamentos"},
        },
        verify_code=uuid4().hex[:8].upper(),
        verify_url=f"https://clinichub.local/verify/{uuid4().hex[:8]}",
    )

    # TODO: persistir (prescriptions table)
    # await db.add(...)
    # await db.commit()

    return out


@router.get("/{prescription_id}", response_model=PrescriptionOut, dependencies=[Depends(require_roles(RoleEnum.doctor, RoleEnum.admin))])
async def get_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # TODO: traer desde DB y mapear a PrescriptionOut
    raise HTTPException(status_code=501, detail="Aún no implementado (persistencia)")
