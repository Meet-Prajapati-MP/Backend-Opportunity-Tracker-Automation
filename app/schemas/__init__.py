from app.schemas.opportunity import Opportunity, OpportunityCreate, OpportunityUpdate
from app.schemas.application import ApplicationTracking, ApplicationTrackingCreate, ApplicationTrackingUpdate
from app.schemas.log import ScraperLog, ScraperLogCreate, AIExtractionLog, AIExtractionLogCreate

__all__ = [
    "Opportunity", "OpportunityCreate", "OpportunityUpdate",
    "ApplicationTracking", "ApplicationTrackingCreate", "ApplicationTrackingUpdate",
    "ScraperLog", "ScraperLogCreate",
    "AIExtractionLog", "AIExtractionLogCreate"
]
