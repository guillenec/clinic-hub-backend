from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
import uuid

from app.core.db import get_db
from app.schemas.certificate import CertificateCreate, CertificateUpdate, CertificateOut
from app.models.certificate import Certificate
from app.models.doctor import Doctor
from ._helpers import gen_code

router = APIRouter(prefix="/clinical/certificates", tags=["Clinical - Certificates"])

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

@router.post("", response_model=CertificateOut)
async def create_certificate(payload: CertificateCreate, db: AsyncSession = Depends(get_db)):
    cert = Certificate(
        id=str(uuid.uuid4()),
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        issued_date=payload.issued_date or date.today(),
        type=payload.type,
        reason=payload.reason,
        rest_days=payload.rest_days,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
        include_signature=payload.include_signature,
        include_stamp=payload.include_stamp,
        verify_code=gen_code(8),
    )
    db.add(cert)
    await db.flush()
    await db.commit()
    await db.refresh(cert)

    out = CertificateOut.model_validate(cert)
    out.doctor = await _doctor_snapshot(db, cert.doctor_id)
    return out

@router.get("", response_model=List[CertificateOut])
async def list_certificates(
    db: AsyncSession = Depends(get_db),
    patient_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = select(Certificate).order_by(Certificate.created_at.desc())
    if patient_id:
        q = q.where(Certificate.patient_id == patient_id)
    if doctor_id:
        q = q.where(Certificate.doctor_id == doctor_id)

    rows = list((await db.execute(q.offset(offset).limit(limit))).scalars())
    out: List[CertificateOut] = []
    for cert in rows:
        dto = CertificateOut.model_validate(cert)
        dto.doctor = await _doctor_snapshot(db, cert.doctor_id)
        out.append(dto)
    return out

@router.get("/{cert_id}", response_model=CertificateOut)
async def get_certificate(cert_id: str, db: AsyncSession = Depends(get_db)):
    cert = (await db.execute(select(Certificate).where(Certificate.id == cert_id))).scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    out = CertificateOut.model_validate(cert)
    out.doctor = await _doctor_snapshot(db, cert.doctor_id)
    return out

@router.patch("/{cert_id}", response_model=CertificateOut)
async def update_certificate(cert_id: str, patch: CertificateUpdate, db: AsyncSession = Depends(get_db)):
    cert = (await db.execute(select(Certificate).where(Certificate.id == cert_id))).scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(cert, k, v)

    await db.flush()
    await db.commit()
    await db.refresh(cert)

    out = CertificateOut.model_validate(cert)
    out.doctor = await _doctor_snapshot(db, cert.doctor_id)
    return out

@router.delete("/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certificate(cert_id: str, db: AsyncSession = Depends(get_db)):
    cert = (await db.execute(select(Certificate).where(Certificate.id == cert_id))).scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    await db.delete(cert)
    await db.commit()
