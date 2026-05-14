import uuid
from sqlalchemy import String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedModel
from typing import Optional, Dict, Any

class ScraperLog(TimeStampedModel):
    __tablename__ = "scraper_logs"

    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g., success, failed, running
    records_found: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    execution_time_ms: Mapped[Optional[int]] = mapped_column()


class AIExtractionLog(TimeStampedModel):
    __tablename__ = "ai_extraction_logs"

    opportunity_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., openai, gemini
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column()
    completion_tokens: Mapped[Optional[int]] = mapped_column()
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    opportunity: Mapped[Optional["Opportunity"]] = relationship("Opportunity", back_populates="ai_logs")
