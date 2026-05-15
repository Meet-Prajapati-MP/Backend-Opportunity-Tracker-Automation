from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.compat import FrontendTrackedOpportunity, serialize_tracking
from app.db.database import get_db
from app.schemas.application import ApplicationTracking, ApplicationTrackingCreate, ApplicationTrackingUpdate
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/tracking", tags=["tracking"])

def get_tracking_service(db: AsyncSession = Depends(get_db)) -> TrackingService:
    return TrackingService(db)

class TrackingStatus(str, Enum):
    saved = "Saved"
    planning = "Planning"
    applied = "Applied"
    interview = "Interview"
    accepted = "Accepted"
    rejected = "Rejected"
    waitlisted = "Waitlisted"

class TrackingSaveRequest(BaseModel):
    opportunity_id: UUID
    status: TrackingStatus = TrackingStatus.saved
    notes: Optional[str] = None
    priority: Optional[str] = Field(None, description="Priority level (e.g., High, Medium, Low)")
    timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline details for the application")

class TrackingStatusUpdate(BaseModel):
    tracking_id: UUID
    status: TrackingStatus
    notes: Optional[str] = None
    priority: Optional[str] = Field(None, description="Priority level")
    timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline details")

async def _save_tracking_impl(
    request: TrackingSaveRequest,
    service: TrackingService = Depends(get_tracking_service)
):
    create_data = ApplicationTrackingCreate(
        opportunity_id=request.opportunity_id,
        status=request.status.value.lower(),
        notes=request.notes
    )
    created = await service.create(create_data)
    refreshed = await service.get_by_id(created.id)
    return serialize_tracking(refreshed or created)

@router.post("", response_model=FrontendTrackedOpportunity, status_code=status.HTTP_201_CREATED)
async def save_tracking(
    request: TrackingSaveRequest,
    service: TrackingService = Depends(get_tracking_service)
):
    return await _save_tracking_impl(request=request, service=service)

@router.post("/save", response_model=FrontendTrackedOpportunity, status_code=status.HTTP_201_CREATED)
async def save_tracking_legacy(
    request: TrackingSaveRequest,
    service: TrackingService = Depends(get_tracking_service)
):
    return await _save_tracking_impl(request=request, service=service)

class TrackingStatusPatchRequest(BaseModel):
    status: str
    notes: Optional[str] = None

async def _update_tracking_impl(
    tracking_id: UUID,
    status: str,
    notes: Optional[str],
    service: TrackingService = Depends(get_tracking_service)
):
    update_schema = ApplicationTrackingUpdate(
        status=status.lower(),
        notes=notes
    )
    result = await service.update(tracking_id, update_schema)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tracking record not found"
        )
    refreshed = await service.get_by_id(result.id)
    return serialize_tracking(refreshed or result)

@router.patch("/{id}", response_model=FrontendTrackedOpportunity)
async def update_tracking_status_by_id(
    id: UUID,
    payload: TrackingStatusPatchRequest,
    service: TrackingService = Depends(get_tracking_service)
):
    return await _update_tracking_impl(tracking_id=id, status=payload.status, notes=payload.notes, service=service)

@router.patch("/status", response_model=FrontendTrackedOpportunity)
async def update_tracking_status(
    update_data: TrackingStatusUpdate,
    service: TrackingService = Depends(get_tracking_service)
):
    return await _update_tracking_impl(tracking_id=update_data.tracking_id, status=update_data.status.value, notes=update_data.notes, service=service)

@router.get("", response_model=List[FrontendTrackedOpportunity])
async def list_tracking(
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=100, description="Pagination limit"),
    service: TrackingService = Depends(get_tracking_service)
):
    items = await service.get_all(skip=skip, limit=limit)
    return [serialize_tracking(item) for item in items]

@router.get("/list", response_model=List[FrontendTrackedOpportunity])
async def list_tracking(
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=100, description="Pagination limit"),
    service: TrackingService = Depends(get_tracking_service)
):
    items = await service.get_all(skip=skip, limit=limit)
    return [serialize_tracking(item) for item in items]

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracking(
    id: UUID,
    service: TrackingService = Depends(get_tracking_service)
):
    if hasattr(service, 'delete'):
        success = await service.delete(id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tracking record not found"
            )
        return None
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, 
        detail="Delete functionality not yet implemented in service layer"
    )
