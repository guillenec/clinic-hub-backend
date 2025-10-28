from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import RoleEnum


bearer = HTTPBearer(auto_error=True)

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub: str | None = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == sub))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    return user

# --- Role-based dependency ---
from fastapi import Depends, HTTPException, status
from app.models.user import User, RoleEnum
# from app.api.deps import get_current_user  # ya existe arriba 

def require_roles(*roles: RoleEnum):
    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado")
        return user
    return _guard

# --- Obtener IDs vinculados ---
# async def get_linked_doctor_id(user: User, db: AsyncSession) -> str | None:
#     if user.role != user.role.doctor:  # comparando enum con string puede fallar, mejor:
#         pass
#     if str(user.role) != "doctor":
#         return None
#     res = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
#     return res.scalar_one_or_none()

# async def get_linked_patient_id(user: User, db: AsyncSession) -> str | None:
#     if str(user.role) != "patient":
#         return None
#     res = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
#     return res.scalar_one_or_none()

# --- Obtener IDs vinculados ---
async def get_linked_doctor_id(user: User, db: AsyncSession) -> str | None:
    if user.role != RoleEnum.doctor:
        return None
    res = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    return res.scalar_one_or_none()

async def get_linked_patient_id(user: User, db: AsyncSession) -> str | None:
    if user.role != RoleEnum.patient:
        return None
    res = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
    return res.scalar_one_or_none()

# -- requiere ser doctor o admin, o ser el doctor dueño del perfil ---
async def require_doctor_owner(
    doctor_id: str,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # admin siempre tiene permiso
    if current.role == RoleEnum.admin:
        return

    # si es doctor, debe ser su propio perfil
    if current.role == RoleEnum.doctor:
        res = await db.execute(select(Doctor.id).where(Doctor.user_id == current.id))
        my_doc_id = res.scalar_one_or_none()
        if my_doc_id == doctor_id:
            return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado")

# --- WebSocket ---
from app.core.config import settings
from fastapi import WebSocket
from typing import Optional

async def get_current_user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub: Optional[str] = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    res = await db.execute(select(User).where(User.id == sub))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    return user

async def get_current_user_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)) -> User:
    """
    Lee ?token=... del query string (o header Authorization) y retorna el User.
    """
    token = ws.query_params.get("token")
    if not token:
        # fallback por si querés mandar Authorization: Bearer xxx en WebSocket
        auth = ws.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        # No podés levantar HTTPException en WebSocket; cerramos con código policy violation
        await ws.close(code=1008)
        raise RuntimeError("WS sin token")
    return await get_current_user_from_token(token, db)
