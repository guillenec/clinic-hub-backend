# app/api/zoom.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.api.deps import get_current_user
from app.services.zoom_oauth import ZOOM_AUTH, CLIENT_ID, REDIRECT_URI, exchange_code_for_tokens, create_meeting
from app.models.appointment import Appointment, ApptType
from app.models.zoom import AppointmentZoom
from datetime import datetime, timezone
import os
from typing import cast
from fastapi import HTTPException
from app.models.doctor import Doctor


router = APIRouter(prefix="/zoom", tags=["zoom"])

# @router.get("/oauth/start")
# async def oauth_start():
#     url = (f"{ZOOM_AUTH}"
#            f"?response_type=code&client_id={CLIENT_ID}"
#            f"&redirect_uri={REDIRECT_URI}")
#     return RedirectResponse(url)

@router.get("/oauth/start")
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

@router.get("/oauth/callback")
async def oauth_cb(code: str = Query(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await exchange_code_for_tokens(db, user.id, code)
    # redirigí a tu front si querés
    return {"ok": True, "message": "Zoom conectado"}

# @router.post("/appointments/{appointment_id}/ensure-meeting")
# async def ensure_meeting(appointment_id: str,
#                          db: AsyncSession = Depends(get_db),
#                          user=Depends(get_current_user)):
#     # 1) Traer turno (verifica permisos si sos doctor/adm/paciente)
#     res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
#     ap = res.scalar_one_or_none()
#     if not ap or ap.type != "virtual":
#         return {"ok": False, "reason": "Turno inexistente o no virtual"}

#     # 2) Ya existe?
#     existing = await db.get(AppointmentZoom, appointment_id)
#     if existing:
#         return {"ok": True, "meeting": {
#             "meeting_id": existing.meeting_id, "start_url": existing.start_url,
#             "join_url": existing.join_url, "passcode": existing.passcode
#         }}

#     # 3) Crear meeting con la cuenta Zoom del doctor (host)
#     topic = f"{os.getenv('APP_NAME','Clinic')}: {ap.patient_id} con {ap.doctor_id}"
#     # start_time en UTC ISO sin microsegundos
#     start = ap.starts_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
#     duration_min = max(15, int((ap.ends_at - ap.starts_at).seconds / 60))  # mínimo 15
#     data = await create_meeting(db, user_id=ap.doctor_id, topic=topic, start_time_iso=start, duration_min=duration_min)
#     # data = await create_meeting(db, user_id=ap.doctor_id, topic=topic,start_time_iso=start, duration_min=int((ap.ends_at - ap.starts_at).seconds/60))

#     z = AppointmentZoom(
#         appointment_id=appointment_id,
#         meeting_id=str(data["id"]),
#         start_url=data["start_url"],
#         join_url=data["join_url"],
#         passcode=data.get("password","")
#     )
#     db.add(z); await db.commit()
#     return {"ok": True, "meeting": {
#         "meeting_id": z.meeting_id, "start_url": z.start_url,
#         "join_url": z.join_url, "passcode": z.passcode
#     }}



@router.post("/appointments/{appointment_id}/ensure-meeting")
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
