from fastapi import APIRouter

from app.api.ai import router as ai_router
from app.api.dashboard import router as dashboard_router
from app.api.opportunities import router as opportunities_router
from app.api.tracking import router as tracking_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(dashboard_router)
api_router.include_router(opportunities_router)
api_router.include_router(tracking_router)
