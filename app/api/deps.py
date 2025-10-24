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
async def get_linked_doctor_id(user: User, db: AsyncSession) -> str | None:
    if user.role != user.role.doctor:  # comparando enum con string puede fallar, mejor:
        pass
    if str(user.role) != "doctor":
        return None
    res = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    return res.scalar_one_or_none()

async def get_linked_patient_id(user: User, db: AsyncSession) -> str | None:
    if str(user.role) != "patient":
        return None
    res = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
    return res.scalar_one_or_none()
