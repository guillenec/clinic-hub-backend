import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.zoom import ZoomToken
from app.core.config import settings  # ✅ usa tu clase Settings
from sqlalchemy import select


ZOOM_AUTH = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN = "https://zoom.us/oauth/token"
ZOOM_REVOKE = "https://zoom.us/oauth/revoke"  # 👈 nuevo
ZOOM_API   = "https://api.zoom.us/v2"

CLIENT_ID = settings.ZOOM_CLIENT_ID
CLIENT_SECRET = settings.ZOOM_CLIENT_SECRET
REDIRECT_URI = settings.ZOOM_REDIRECT_URL

def basic_auth_header():
    import base64
    b = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {b}"}

async def exchange_code_for_tokens(db: AsyncSession, user_id: str, code: str):
    async with httpx.AsyncClient() as cx:
        r = await cx.post(
            ZOOM_TOKEN,
            params={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
            headers=basic_auth_header(),
        )
    if r.status_code != 200:
        raise HTTPException(400, f"Zoom token error: {r.text}")
    data = r.json()
    exp = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]) - 60)
    zt = ZoomToken(
        user_id=user_id,
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=exp,
    )
    await db.merge(zt)
    await db.commit()
    return zt

async def ensure_access_token(db: AsyncSession, user_id: str) -> str:
    res = await db.execute(select(ZoomToken).where(ZoomToken.user_id==user_id))
    zt = res.scalar_one_or_none()
    if not zt:
        raise HTTPException(400, "Zoom no conectado para este usuario.")
    if zt.expires_at <= datetime.utcnow():
        # refresh
        async with httpx.AsyncClient() as cx:
            r = await cx.post(
                ZOOM_TOKEN,
                params={"grant_type": "refresh_token", "refresh_token": zt.refresh_token},
                headers=basic_auth_header(),
            )
        if r.status_code != 200:
            raise HTTPException(400, f"Zoom refresh error: {r.text}")
        d = r.json()
        exp = datetime.utcnow() + timedelta(seconds=int(d["expires_in"]) - 60)
        await db.execute(update(ZoomToken).where(ZoomToken.user_id==user_id).values(
            access_token=d["access_token"], refresh_token=d["refresh_token"], expires_at=exp
        ))
        await db.commit()
        return d["access_token"]
    return zt.access_token

# async def create_meeting(db: AsyncSession, user_id: str, topic: str, start_time_iso: str, duration_min: int):
#     token = await ensure_access_token(db, user_id)
#     payload = {
#         "topic": topic,
#         "type": 2,  # scheduled
#         "start_time": start_time_iso,  # ISO8601 UTC
#         "duration": duration_min,
#         "settings": {
#             "waiting_room": True,
#             "join_before_host": False,
#             "mute_upon_entry": True,
#             "approval_type": 0,  # automatically approve
#             "audio": "voip",
#             "encryption_type": "enhanced_encryption",
#         }
#     }
#     async with httpx.AsyncClient() as cx:
#         r = await cx.post(f"{ZOOM_API}/users/me/meetings",
#                           json=payload,
#                           headers={"Authorization": f"Bearer {token}"})
#     if r.status_code not in (200,201):
#         raise HTTPException(400, f"Create meeting error: {r.text}")
#     return r.json()

async def create_meeting(
    db,
    user_id: str,
    topic: str,
    start_time_iso: str,
    duration_min: int,
) -> dict:
    """
    Crea una reunión en Zoom para el user_id (host).
    Garantiza un access_token válido haciendo refresh si hace falta.
    """
    # 🔐 garantizar token válido
    access_token = await refresh_zoom_token(db, user_id)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "topic": topic,
        "type": 2,  # scheduled
        "start_time": start_time_iso,  # ISO UTC
        "duration": duration_min,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "waiting_room": True,
            "join_before_host": False,
            "mute_upon_entry": True,
            "approval_type": 0,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.zoom.us/v2/users/{user_id}/meetings",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

async def refresh_zoom_token(db, user_id: str):
    """
    Refresca el token de Zoom si está vencido.
    Devuelve un access_token válido (viejo o nuevo).
    """
    res = await db.execute(select(ZoomToken).where(ZoomToken.user_id == user_id))
    token = res.scalar_one_or_none()
    if not token:
        raise ValueError("Zoom no conectado para este usuario.")

    # si faltan más de 5 minutos para vencer, devolvemos el actual
    now = datetime.now(timezone.utc)
    if token.expires_at > now + timedelta(minutes=5):
        return token.access_token

    # si está vencido o por vencer, pedimos uno nuevo
    print("🔄 Refreshing Zoom token...")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token,
    }
    auth = (settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET)

    async with httpx.AsyncClient() as client:
        resp = await client.post("https://zoom.us/oauth/token", data=data, auth=auth)
        resp.raise_for_status()
        payload = resp.json()

    token.access_token = payload["access_token"]
    token.refresh_token = payload["refresh_token"]
    token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=payload["expires_in"])
    await db.commit()
    await db.refresh(token)

    print("✅ Zoom token actualizado para usuario:", user_id)
    return token.access_token

async def revoke_zoom_token(db: AsyncSession, user_id: str) -> dict:
    """Intenta revocar en Zoom y borra el token localmente."""
    res = await db.execute(select(ZoomToken).where(ZoomToken.user_id == user_id))
    zt = res.scalar_one_or_none()
    if not zt:
        return {"ok": True, "revoked": False, "detail": "No había token guardado"}

    # Zoom permite revocar con access_token o refresh_token. Usamos refresh_token.
    try:
        async with httpx.AsyncClient() as cx:
            # Zoom espera x-www-form-urlencoded + Basic Auth
            await cx.post(
                ZOOM_REVOKE,
                data={"token": zt.refresh_token},
                headers=basic_auth_header(),
                timeout=10.0,
            )
    except Exception:
        # No bloqueamos si falla: continuamos con el borrado local.
        pass

    # Borrado local
    await db.delete(zt)
    await db.commit()
    return {"ok": True, "revoked": True}