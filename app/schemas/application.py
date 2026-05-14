from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class ApplicationTrackingBase(BaseModel):
    opportunity_id: UUID
    status: str = "saved"
    applied_date: Optional[date] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None

class ApplicationTrackingCreate(ApplicationTrackingBase):
    pass

class ApplicationTrackingUpdate(BaseModel):
    status: Optional[str] = None
    applied_date: Optional[date] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None

class ApplicationTrackingInDBBase(ApplicationTrackingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApplicationTracking(ApplicationTrackingInDBBase):
    pass
