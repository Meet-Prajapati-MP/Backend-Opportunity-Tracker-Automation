from pydantic import BaseModel, HttpUrl, ConfigDict
from typing import Optional
from datetime import date, datetime
from uuid import UUID

class OpportunityBase(BaseModel):
    title: str
    company: str
    url: str # Accepting string here but can be updated to HttpUrl if strict validation needed from client
    location: Optional[str] = None
    description: Optional[str] = None
    salary_range: Optional[str] = None
    posted_date: Optional[date] = None
    is_active: bool = True
    source: Optional[str] = None

class OpportunityCreate(OpportunityBase):
    pass

class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    url: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_range: Optional[str] = None
    posted_date: Optional[date] = None
    is_active: Optional[bool] = None
    source: Optional[str] = None

class OpportunityInDBBase(OpportunityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Opportunity(OpportunityInDBBase):
    pass
