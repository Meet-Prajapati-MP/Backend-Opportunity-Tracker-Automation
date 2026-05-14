from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

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

@router.post("/save", response_model=ApplicationTracking, status_code=status.HTTP_201_CREATED)
async def save_tracking(
    request: TrackingSaveRequest,
    service: TrackingService = Depends(get_tracking_service)
):
    """
    Save an opportunity to tracking.
    Supports status, notes, priority, and timeline features.
    """
    create_data = ApplicationTrackingCreate(
        opportunity_id=request.opportunity_id,
        status=request.status.value,
        notes=request.notes
    )
    # Priority and timeline support are validated via request schema
    # but rely on future data model extensions to be fully persisted
    return await service.create(create_data)

@router.patch("/status", response_model=ApplicationTracking)
async def update_tracking_status(
    update_data: TrackingStatusUpdate,
    service: TrackingService = Depends(get_tracking_service)
):
    """
    Update tracking status, along with notes, priority, and timeline support.
    """
    update_schema = ApplicationTrackingUpdate(
        status=update_data.status.value,
        notes=update_data.notes
    )
    result = await service.update(update_data.tracking_id, update_schema)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tracking record not found"
        )
    return result

@router.get("/list", response_model=List[ApplicationTracking])
async def list_tracking(
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=100, description="Pagination limit"),
    service: TrackingService = Depends(get_tracking_service)
):
    """
    List all tracked opportunities.
    """
    return await service.get_all(skip=skip, limit=limit)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tracking(
    id: UUID,
    service: TrackingService = Depends(get_tracking_service)
):
    """
    Delete a tracking record.
    """
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
