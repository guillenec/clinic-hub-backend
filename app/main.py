from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.clinic import router as clinic_router
from app.api.v1.doctor import router as doctor_router
from app.api.v1.patient import router as patient_router
from app.api.v1.appointment import router as appointment_router
# from app.api.v1.clinical import router as clinical_router
from app.api.v1.files import router as files_router
from app.api.v1.prescriptions import router as prescriptions_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.clinical.consultations import router as consultations_router
from app.api.v1.clinical.medications import router as medications_router
from app.api.v1.clinical.labs import router as labs_router
from app.api.v1.clinical.vitals import router as vitals_router
from app.api.v1.zoom import router as zoom_router
from app.api.v1.ws_chat import router as ws_chat_router


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
# app.include_router(clinical_router)
app.include_router(files_router)
app.include_router(prescriptions_router)
app.include_router(certificates_router)
app.include_router(consultations_router)
app.include_router(medications_router)
app.include_router(labs_router)
app.include_router(vitals_router)

app.include_router(zoom_router, prefix="/api/vq", tags=["zoom"])
app.include_router(ws_chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}