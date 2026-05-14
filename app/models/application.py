import uuid
from sqlalchemy import String, ForeignKey, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedModel
from typing import Optional
from datetime import date

class ApplicationTracking(TimeStampedModel):
    __tablename__ = "application_tracking"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="saved", index=True) # e.g., saved, applied, interviewing, rejected, offered
    applied_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    resume_version: Mapped[Optional[str]] = mapped_column(String(100))
    
    opportunity: Mapped["Opportunity"] = relationship("Opportunity", back_populates="applications")
