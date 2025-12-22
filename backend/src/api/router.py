from fastapi import APIRouter

from src.api.clinicians import router as clinicians_router
from src.api.patients import router as patients_router
from src.api.sessions import router as sessions_router
from src.api.assessment import router as assessment_router
from src.api.memory import router as memory_router
from src.api.analytics import router as analytics_router
from src.vapi.webhooks import router as vapi_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(clinicians_router)
api_router.include_router(patients_router)
api_router.include_router(sessions_router)
api_router.include_router(assessment_router)
api_router.include_router(memory_router)
api_router.include_router(analytics_router)
api_router.include_router(vapi_router)
