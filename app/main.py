from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.clinic import router as clinic_router
from app.api.v1.doctor import router as doctor_router
from app.api.v1.patient import router as patient_router
from app.api.v1.appointment import router as appointment_router


app = FastAPI(title="Clinic Hub API", version="0.1.0")

# 🔓 ajustá origins con tu URL de Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(clinic_router)
app.include_router(doctor_router)
app.include_router(patient_router)
app.include_router(appointment_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
