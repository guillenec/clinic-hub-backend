from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    generate_2fa_secret, totp_uri_from_secret, verify_totp, qr_png_base64_from_text
)
from app.models.user import User, RoleEnum
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut, TwoFASetupOut, TwoFAVerifyIn, TwoFADisableIn, LoginOut
from app.api.deps import get_current_user, get_linked_doctor_id, get_linked_patient_id

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User).where(User.email == payload.email.lower()))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=RoleEnum(payload.role.value),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    # Si 2FA está activo, validar otp (esto ya lo tenías hecho; mantén la misma lógica)
    if user.is_2fa_enabled:
        if not payload.otp:
            raise HTTPException(status_code=401, detail="Se requiere OTP (2FA) para este usuario")
        from app.core.security import verify_totp
        if not user.twofa_secret or not verify_totp(payload.otp, user.twofa_secret):
            raise HTTPException(status_code=401, detail="OTP inválido")

    token = create_access_token(subject=user.id, extra={"role": user.role.value})

    # 🔗 perfiles vinculados (si existen)
    linked_doc_id = await get_linked_doctor_id(user, db)
    linked_pat_id = await get_linked_patient_id(user, db)

    return LoginOut(
        access_token=token,
        user=UserOut.model_validate(user),
        linkedDoctorId=linked_doc_id,
        linkedPatientId=linked_pat_id,
    )

# ---------- 2FA FLOW ----------
@router.post("/2fa/setup", response_model=TwoFASetupOut)
async def twofa_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # generar secreto nuevo (si ya tenía, lo reemplazamos hasta que confirme)
    secret = generate_2fa_secret()
    current_user.twofa_secret = secret
    # aún no habilitado
    current_user.is_2fa_enabled = False
    await db.commit()

    otpauth = totp_uri_from_secret(secret, email=current_user.email, issuer="Clinic Hub")
    qr_b64 = qr_png_base64_from_text(otpauth) or None
    return TwoFASetupOut(secret=secret, otpauth_url=otpauth, qr_base64_png=qr_b64)

@router.post("/2fa/enable")
async def twofa_enable(
    body: TwoFAVerifyIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.twofa_secret:
        raise HTTPException(status_code=400, detail="No hay secreto 2FA configurado. Ejecutá /auth/2fa/setup")
    if not verify_totp(body.otp, current_user.twofa_secret):
        raise HTTPException(status_code=400, detail="OTP inválido")
    current_user.is_2fa_enabled = True
    await db.commit()
    return {"ok": True}

@router.post("/2fa/disable")
async def twofa_disable(
    body: TwoFADisableIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.is_2fa_enabled or not current_user.twofa_secret:
        # ya está deshabilitado
        current_user.is_2fa_enabled = False
        current_user.twofa_secret = None
        await db.commit()
        return {"ok": True}

    if not verify_totp(body.otp, current_user.twofa_secret):
        raise HTTPException(status_code=400, detail="OTP inválido")

    current_user.is_2fa_enabled = False
    current_user.twofa_secret = None
    await db.commit()
    return {"ok": True}


# @router.get("/me", response_model=UserOut)
# async def me(current_user: User = Depends(get_current_user)):
#     return current_user

@router.get("/me", response_model=LoginOut)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    token = create_access_token(subject=current_user.id, extra={"role": current_user.role.value})
    linked_doc_id = await get_linked_doctor_id(current_user, db)
    linked_pat_id = await get_linked_patient_id(current_user, db)
    return LoginOut(
        access_token=token,
        user=UserOut.model_validate(current_user),
        linkedDoctorId=linked_doc_id,
        linkedPatientId=linked_pat_id,
    )