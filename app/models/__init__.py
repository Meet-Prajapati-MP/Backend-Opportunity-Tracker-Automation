from app.models.base import TimeStampedModel
from app.models.opportunity import Opportunity
from app.models.application import ApplicationTracking
from app.models.log import ScraperLog, AIExtractionLog

# For Alembic to find all models easily
__all__ = [
    "TimeStampedModel",
    "Opportunity",
    "ApplicationTracking",
    "ScraperLog",
    "AIExtractionLog"
]
