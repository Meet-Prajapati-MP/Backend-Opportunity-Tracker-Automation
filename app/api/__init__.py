from fastapi import APIRouter

from app.api.opportunities import router as opportunities_router
from app.api.tracking import router as tracking_router

api_router = APIRouter()
api_router.include_router(opportunities_router)
api_router.include_router(tracking_router)
