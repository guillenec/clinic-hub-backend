# app/api/zoom.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.db import get_db
from app.api.deps import get_current_user
from app.services.zoom_oauth import (
    ZOOM_AUTH, CLIENT_ID, REDIRECT_URI,
    exchange_code_for_tokens, create_meeting, revoke_zoom_token
)
from app.models.appointment import Appointment, ApptType
from app.models.zoom import AppointmentZoom
from datetime import datetime, timedelta, timezone
import os
from typing import cast
from fastapi import HTTPException
from app.models.doctor import Doctor
from app.models.user import RoleEnum
from app.models.patient import Patient

from app.schemas.zoom import (
    ZoomMeetingCreateResponse,
    ZoomLinkOut,
    ZoomTokenOut,
    ZoomCleanupOut,
)

router = APIRouter(prefix="/zoom", tags=["zoom"])

@router.get("/oauth/start", response_model=dict)
async def oauth_start():
    url = (f"{ZOOM_AUTH}"
           f"?response_type=code&client_id={CLIENT_ID}"
           f"&redirect_uri={REDIRECT_URI}")
    return {"auth_url": url}  # <- así Swagger ya no falla

@router.get("/oauth/start/redirect")
async def oauth_start_redirect():
    url = (f"{ZOOM_AUTH}"
           f"?response_type=code&client_id={CLIENT_ID}"
           f"&redirect_uri={REDIRECT_URI}")
    return RedirectResponse(url)

# @router.get("/oauth/callback", response_model=ZoomTokenOut)
# async def oauth_cb(code: str = Query(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
#     await exchange_code_for_tokens(db, user.id, code)
#     # redirigí a tu front si querés
#     return {"ok": True, "message": "Zoom conectado"}

@router.get("/oauth/callback", response_model=ZoomTokenOut)
async def oauth_cb(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    zt = await exchange_code_for_tokens(db, user.id, code)  # <- obtiene ZoomToken
    return ZoomTokenOut(
        user_id=zt.user_id,
        access_token=zt.access_token,
        refresh_token=zt.refresh_token,
        expires_at=zt.expires_at,
    )

@router.post("/appointments/{appointment_id}/ensure-meeting",
             response_model=ZoomMeetingCreateResponse
             )
async def ensure_meeting(
    
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    # 1) Buscar turno
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    ap = res.scalar_one_or_none()
    if not ap or ap.type != "virtual":
        return {"ok": False, "reason": "Turno inexistente o no virtual"}

    # 2) Ya existe meeting?
    existing = await db.get(AppointmentZoom, appointment_id)
    if existing:
        return {"ok": True, "meeting": {
            "meeting_id": existing.meeting_id,
            "start_url": existing.start_url,
            "join_url": existing.join_url,
            "passcode": existing.passcode
        }}

    # 3) Obtener el user_id del doctor (no su id de tabla doctors)
    q = await db.execute(select(Doctor).where(Doctor.id == ap.doctor_id))
    doc = q.scalar_one_or_none()
    # if not doc:
    #     return {"ok": False, "reason": "Doctor no encontrado"}
    if not doc:
        raise HTTPException(404, "Doctor no encontrado")
    if not doc.user_id:
        raise HTTPException(400, "Doctor sin usuario vinculado")
    
    if not ap or ap.type != ApptType.virtual:
        return {"ok": False, "reason": "Turno inexistente o no virtual"}
    
    # si es naive, lo marcamos como UTC antes de serializar
    start_dt = ap.starts_at
    

    # 4) Crear la reunión usando el user_id del doctor
    topic = f"{os.getenv('APP_NAME','Clinic')}: {ap.patient_id} con {ap.doctor_id}"
    # start = ap.starts_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    start = start_dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    duration_min = max(15, int((ap.ends_at - ap.starts_at).seconds / 60))

    user_id_for_zoom = cast(str, doc.user_id)  # 👈 asegura str para el type checker

    # access_token = await refresh_zoom_token(db, user_id_for_zoom)

    data = await create_meeting(
        db,
        user_id=user_id_for_zoom,  # 👈 acá va el user_id correcto
        topic=topic,
        start_time_iso=start,
        duration_min=duration_min
    )

    z = AppointmentZoom(
        appointment_id=appointment_id,
        meeting_id=str(data["id"]),
        start_url=data["start_url"],
        join_url=data["join_url"],
        passcode=data.get("password", "")
    )
    db.add(z)
    await db.commit()

    return {
        "ok": True,
        "meeting": {
            "meeting_id": z.meeting_id,
            "start_url": z.start_url,
            "join_url": z.join_url,
            "passcode": z.passcode
        }
    }

@router.get("/appointments/{appointment_id}/link",
            response_model=ZoomLinkOut
            )
async def get_zoom_link(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    # Traer turno + verificación de acceso por rol
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    ap = res.scalar_one_or_none()
    if not ap:
        raise HTTPException(404, "Turno no encontrado")
    if ap.type != ApptType.virtual:
        raise HTTPException(400, "El turno no es virtual")

    # Encontrar reunión ya creada
    zoom = await db.get(AppointmentZoom, appointment_id)
    if not zoom:
        raise HTTPException(404, "Aún no hay reunión. Ejecutá /zoom/appointments/{id}/ensure-meeting")

    # Verificaciones de pertenencia según rol
    if user.role == RoleEnum.doctor:
        qdoc = await db.execute(select(Doctor).where(Doctor.user_id == user.id))
        doc = qdoc.scalar_one_or_none()
        if not doc or doc.id != ap.doctor_id:
            raise HTTPException(403, "No autorizado para este turno")
        return {"url": zoom.start_url, "kind": "start_url"}

    if user.role == RoleEnum.patient:
        qpat = await db.execute(select(Patient).where(Patient.user_id == user.id))
        pat = qpat.scalar_one_or_none()
        if not pat or pat.id != ap.patient_id:
            raise HTTPException(403, "No autorizado para este turno")
        return {"url": zoom.join_url, "kind": "join_url"}

    # Admin
    if user.role == RoleEnum.admin:
        return {"url": zoom.start_url, "kind": "start_url"}

    raise HTTPException(403, "Rol no soportado")
    

@router.delete("/disconnect", response_model=ZoomTokenOut)
async def zoom_disconnect(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Revoca el token en Zoom (si puede) y borra credenciales locales.
    Solo afecta al usuario autenticado.
    """
    result = await revoke_zoom_token(db, user.id)
    return result

@router.post("/maintenance/cleanup", response_model=ZoomCleanupOut)
async def cleanup_old_zooms(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.role != RoleEnum.admin:
        raise HTTPException(403, "Solo administradores")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Traer IDs de appointments viejos para borrar sus zooms
    ap_ids = (await db.execute(
        select(Appointment.id).where(Appointment.ends_at < cutoff)
    )).scalars().all()

    if not ap_ids:
        return {"deleted": 0, "cutoff": cutoff.isoformat()}

    await db.execute(delete(AppointmentZoom).where(AppointmentZoom.appointment_id.in_(ap_ids)))
    await db.commit()
    return {"deleted": len(ap_ids), "cutoff": cutoff.isoformat()}