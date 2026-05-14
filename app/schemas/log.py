from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ScraperLogBase(BaseModel):
    source: str
    status: str
    records_found: int = 0
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None

class ScraperLogCreate(ScraperLogBase):
    pass

class ScraperLog(ScraperLogBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AIExtractionLogBase(BaseModel):
    opportunity_id: Optional[UUID] = None
    provider: str
    model: str
    status: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class AIExtractionLogCreate(AIExtractionLogBase):
    pass

class AIExtractionLog(AIExtractionLogBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
