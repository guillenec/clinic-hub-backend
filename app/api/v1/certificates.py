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
from app.schemas.certificate import CertificateCreate, CertificateOut
from app.schemas.prescription import DoctorAsset, PatientMini

router = APIRouter(prefix="/clinical/certificates", tags=["clinical"])


@router.post("", response_model=CertificateOut, dependencies=[Depends(require_roles(RoleEnum.doctor, RoleEnum.admin))])
async def create_certificate(
    body: CertificateCreate,
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

    cert_payload = {
        "type": body.type,
        "reason": body.reason,
        "rest_days": body.rest_days,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "notes": body.notes,
    }

    out = CertificateOut(
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
        certificate=cert_payload,
        render={
            "header": {"title": "Certificado médico"},
            "footer": {"disclaimer": "Válido sin enmiendas"},
        },
        verify_code=uuid4().hex[:8].upper(),
        verify_url=f"https://clinichub.local/verify/{uuid4().hex[:8]}",
    )

    # TODO: persistir (certificates table)
    # await db.add(...)
    # await db.commit()

    return out


@router.get("/{certificate_id}", response_model=CertificateOut, dependencies=[Depends(require_roles(RoleEnum.doctor, RoleEnum.admin))])
async def get_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # TODO: traer desde DB y mapear a CertificateOut
    raise HTTPException(status_code=501, detail="Aún no implementado (persistencia)")
