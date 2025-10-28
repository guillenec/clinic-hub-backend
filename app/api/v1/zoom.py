# app/api/zoom.py
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_db
from app.api.deps import get_current_user
from app.services.zoom_oauth import ZOOM_AUTH, CLIENT_ID, REDIRECT_URI, exchange_code_for_tokens, create_meeting
from app.models.appointment import Appointment
from app.models.zoom import AppointmentZoom
from datetime import datetime, timezone
import os

router = APIRouter(prefix="/api/zoom", tags=["zoom"])

@router.get("/oauth/start")
async def oauth_start():
    url = (f"{ZOOM_AUTH}"
           f"?response_type=code&client_id={CLIENT_ID}"
           f"&redirect_uri={REDIRECT_URI}")
    return RedirectResponse(url)

@router.get("/oauth/callback")
async def oauth_cb(code: str = Query(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    await exchange_code_for_tokens(db, user.id, code)
    # redirigí a tu front si querés
    return {"ok": True, "message": "Zoom conectado"}

@router.post("/appointments/{appointment_id}/ensure-meeting")
async def ensure_meeting(appointment_id: str,
                         db: AsyncSession = Depends(get_db),
                         user=Depends(get_current_user)):
    # 1) Traer turno (verifica permisos si sos doctor/adm/paciente)
    res = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    ap = res.scalar_one_or_none()
    if not ap or ap.type != "virtual":
        return {"ok": False, "reason": "Turno inexistente o no virtual"}

    # 2) Ya existe?
    existing = await db.get(AppointmentZoom, appointment_id)
    if existing:
        return {"ok": True, "meeting": {
            "meeting_id": existing.meeting_id, "start_url": existing.start_url,
            "join_url": existing.join_url, "passcode": existing.passcode
        }}

    # 3) Crear meeting con la cuenta Zoom del doctor (host)
    topic = f"{os.getenv('APP_NAME','Clinic')}: {ap.patient_id} con {ap.doctor_id}"
    # start_time en UTC ISO sin microsegundos
    start = ap.starts_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    duration_min = max(15, int((ap.ends_at - ap.starts_at).seconds / 60))  # mínimo 15
    data = await create_meeting(db, user_id=ap.doctor_id, topic=topic, start_time_iso=start, duration_min=duration_min)
    # data = await create_meeting(db, user_id=ap.doctor_id, topic=topic,start_time_iso=start, duration_min=int((ap.ends_at - ap.starts_at).seconds/60))

    z = AppointmentZoom(
        appointment_id=appointment_id,
        meeting_id=str(data["id"]),
        start_url=data["start_url"],
        join_url=data["join_url"],
        passcode=data.get("password","")
    )
    db.add(z); await db.commit()
    return {"ok": True, "meeting": {
        "meeting_id": z.meeting_id, "start_url": z.start_url,
        "join_url": z.join_url, "passcode": z.passcode
    }}



