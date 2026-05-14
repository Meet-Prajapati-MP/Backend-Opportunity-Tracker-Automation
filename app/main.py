from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api import api_router
from app.jobs import create_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

# Include all API routers
app.include_router(api_router, prefix=settings.API_V1_STR)
