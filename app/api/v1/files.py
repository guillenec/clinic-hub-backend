from fastapi import APIRouter, UploadFile, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.config import settings
from app.core.cdn import upload_png, destroy, build_url_with_bg_removal, upload_image_avatar
from app.api.deps import require_roles, require_doctor_owner, get_current_user
from app.models.user import RoleEnum, User
from app.models.doctor import Doctor
from app.models.patient import Patient  
from typing import Optional



MAX_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024


router = APIRouter(prefix="/files", tags=["files"])

async def _read_and_validate_png(file: UploadFile) -> bytes:
    if file.content_type not in {"image/png"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Sólo PNG")
    b = await file.read()
    if len(b) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Máximo {settings.MAX_UPLOAD_MB} MB")
    return b

# 
def _destroy_if_present(public_id: Optional[str]) -> None:
    if public_id:
        destroy(public_id)

async def _read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Sólo PNG o JPG",
        )
    b = await file.read()
    if len(b) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Máximo {settings.MAX_UPLOAD_MB} MB")
    return b

# ---------- helpers de ownership ----------

async def _require_user_owner(user_id: str,
                              current: User = Depends(get_current_user)):
    if current.role == RoleEnum.admin:
        return
    if current.id != user_id:
        raise HTTPException(status_code=403, detail="Permiso denegado")

async def _require_doctor_owner(doctor_id: str,
                                current: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    if current.role == RoleEnum.admin:
        return
    if current.role == RoleEnum.doctor:
        res = await db.execute(select(Doctor.id).where(Doctor.user_id == current.id))
        my_doc_id = res.scalar_one_or_none()
        if my_doc_id == doctor_id:
            return
    raise HTTPException(status_code=403, detail="Permiso denegado")

async def _require_patient_owner(patient_id: str,
                                 current: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_db)):
    if current.role == RoleEnum.admin:
        return
    if current.role == RoleEnum.patient:
        res = await db.execute(select(Patient.id).where(Patient.user_id == current.id))
        my_pt_id = res.scalar_one_or_none()
        if my_pt_id == patient_id:
            return
    raise HTTPException(status_code=403, detail="Permiso denegado")


# ========== AVATAR USUARIO ==========
@router.post("/users/{user_id}/avatar",
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def upload_user_avatar(user_id: str,
                             file: UploadFile,
                             _=Depends(_require_user_owner),
                             db: AsyncSession = Depends(get_db)):
    bits = await _read_and_validate_image(file)
    url, public_id = upload_image_avatar(bits, settings.MEDIA_FOLDER_AVATARS)

    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if getattr(u, "photo_public_id", None):
        # destroy(u.photo_public_id)
        _destroy_if_present(getattr(u, "photo_public_id", None))

    await db.execute(update(User)
                     .where(User.id == user_id)
                     .values(photo_url=url, photo_public_id=public_id))
    await db.commit()
    return {"url": url, "public_id": public_id}

@router.delete("/users/{user_id}/avatar",
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor, RoleEnum.patient))])
async def delete_user_avatar(user_id: str,
                             _=Depends(_require_user_owner),
                             db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if getattr(u, "photo_public_id", None):
        # destroy(u.photo_public_id)
        _destroy_if_present(getattr(u, "photo_public_id", None))


    await db.execute(update(User)
                     .where(User.id == user_id)
                     .values(photo_url=None, photo_public_id=None))
    await db.commit()
    return {"ok": True}


# ========== FOTO DOCTOR ==========
@router.post("/doctors/{doctor_id}/photo",
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def upload_doctor_photo(doctor_id: str,
                              file: UploadFile,
                              _=Depends(_require_doctor_owner),
                              db: AsyncSession = Depends(get_db)):
    bits = await _read_and_validate_image(file)
    url, public_id = upload_image_avatar(bits, settings.MEDIA_FOLDER_PHOTOS)

    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    if getattr(doc, "photo_public_id", None):
        # destroy(doc.photo_public_id)
        _destroy_if_present(getattr(doc, "photo_public_id", None))


    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(photo_url=url, photo_public_id=public_id))
    await db.commit()
    return {"url": url, "public_id": public_id}

@router.delete("/doctors/{doctor_id}/photo",
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.doctor))])
async def delete_doctor_photo(doctor_id: str,
                              _=Depends(_require_doctor_owner),
                              db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor no encontrado")

    if getattr(doc, "photo_public_id", None):
        # destroy(doc.photo_public_id)
        _destroy_if_present(getattr(doc, "photo_public_id", None))


    await db.execute(update(Doctor)
                     .where(Doctor.id == doctor_id)
                     .values(photo_url=None, photo_public_id=None))
    await db.commit()
    return {"ok": True}


# ========== FOTO PACIENTE ==========
@router.post("/patients/{patient_id}/photo",
             dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.patient))])
async def upload_patient_photo(patient_id: str,
                               file: UploadFile,
                               _=Depends(_require_patient_owner),
                               db: AsyncSession = Depends(get_db)):
    bits = await _read_and_validate_image(file)
    url, public_id = upload_image_avatar(bits, settings.MEDIA_FOLDER_PHOTOS)

    res = await db.execute(select(Patient).where(Patient.id == patient_id))
    pt = res.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if getattr(pt, "photo_public_id", None):
        # destroy(pt.photo_public_id)
        _destroy_if_present(getattr(pt, "photo_public_id", None))


    await db.execute(update(Patient)
                     .where(Patient.id == patient_id)
                     .values(photo_url=url, photo_public_id=public_id))
    await db.commit()
    return {"url": url, "public_id": public_id}

@router.delete("/patients/{patient_id}/photo",
               dependencies=[Depends(require_roles(RoleEnum.admin, RoleEnum.patient))])
async def delete_patient_photo(patient_id: str,
                               _=Depends(_require_patient_owner),
                               db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Patient).where(Patient.id == patient_id))
    pt = res.scalar_one_or_none()
    if not pt:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    if getattr(pt, "photo_public_id", None):
        # destroy(pt.photo_public_id)
        _destroy_if_present(getattr(pt, "photo_public_id", None))


    await db.execute(update(Patient)
                     .where(Patient.id == patient_id)
                     .values(photo_url=None, photo_public_id=None))
    await db.commit()
    return {"ok": True}

# ---- -----
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