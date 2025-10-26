from fastapi import APIRouter, UploadFile, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.config import settings
from app.core.cdn import upload_png, destroy, build_url_with_bg_removal
from app.api.deps import require_roles, require_doctor_owner
from app.models.user import RoleEnum
from app.models.doctor import Doctor

MAX_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024

router = APIRouter(prefix="/files", tags=["files"])

async def _read_and_validate_png(file: UploadFile) -> bytes:
    if file.content_type not in {"image/png"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Sólo PNG")
    b = await file.read()
    if len(b) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Máximo {settings.MAX_UPLOAD_MB} MB")
    return b

# --- Firma ---
@router.post("/doctors/{doctor_id}/signature", dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def upload_signature(doctor_id: str,
                           file: UploadFile,
                           _=Depends(require_doctor_owner),
                           db: AsyncSession = Depends(get_db)):
    bits = await _read_and_validate_png(file)
    url, public_id = upload_png(bits, settings.MEDIA_FOLDER_SIGNATURES)

    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    # Borra anterior en Cloudinary si existe
    if doc.signature_public_id:
        destroy(doc.signature_public_id)

    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(signature_png=url, signature_public_id=public_id))
    await db.commit()
    return {"url": url, "public_id": public_id}

@router.delete("/doctors/{doctor_id}/signature", dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_signature(doctor_id: str, _=Depends(require_doctor_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")
    if doc.signature_public_id:
        destroy(doc.signature_public_id)
    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(signature_png=None, signature_public_id=None))
    await db.commit()
    return {"ok": True}

# --- Sello ---
@router.post("/doctors/{doctor_id}/stamp", dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def upload_stamp(doctor_id: str,
                       file: UploadFile,
                       _=Depends(require_doctor_owner),
                       db: AsyncSession = Depends(get_db)):
    bits = await _read_and_validate_png(file)
    url, public_id = upload_png(bits, settings.MEDIA_FOLDER_STAMPS)

    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    if doc.stamp_public_id:
        destroy(doc.stamp_public_id)

    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(stamp_png=url, stamp_public_id=public_id))
    await db.commit()
    return {"url": url, "public_id": public_id}

@router.delete("/doctors/{doctor_id}/stamp", dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_stamp(doctor_id: str, _=Depends(require_doctor_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")
    if doc.stamp_public_id:
        destroy(doc.stamp_public_id)
    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(stamp_png=None, stamp_public_id=None))
    await db.commit()
    return {"ok": True}

# rutas para remover fondo usando Cloudinary
# app/api/v1/files.py
@router.post("/doctors/{doctor_id}/signature/remove-bg")
async def signature_remove_bg(
    doctor_id: str,
    _=Depends(require_doctor_owner),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc or not doc.signature_public_id:
        raise HTTPException(status_code=404, detail="No hay firma para procesar")

    # Sólo actualizamos la URL a la versión transformada
    url = build_url_with_bg_removal(doc.signature_public_id)
    await db.execute(update(Doctor).where(Doctor.id == doctor_id).values(signature_png=url))
    await db.commit()
    return {"url": url}

@router.post("/doctors/{doctor_id}/stamp/remove-bg")
async def stamp_remove_bg(
    doctor_id: str,
    _=Depends(require_doctor_owner),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc or not doc.stamp_public_id:
        raise HTTPException(status_code=404, detail="No hay sello para procesar")

    url = build_url_with_bg_removal(doc.stamp_public_id)
    await db.execute(update(Doctor).where(Doctor.id == doctor_id).values(stamp_png=url))
    await db.commit()
    return {"url": url}