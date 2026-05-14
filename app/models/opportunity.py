from sqlalchemy import String, Text, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedModel
from typing import List, Optional
from datetime import date

class Opportunity(TimeStampedModel):
    __tablename__ = "opportunities"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100))
    posted_date: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[Optional[str]] = mapped_column(String(100))

    applications: Mapped[List["ApplicationTracking"]] = relationship("ApplicationTracking", back_populates="opportunity", cascade="all, delete-orphan")
    ai_logs: Mapped[List["AIExtractionLog"]] = relationship("AIExtractionLog", back_populates="opportunity", cascade="all, delete-orphan")

    __table_args__ = (
        # Prevent duplicate opportunities from the same company/url
        UniqueConstraint('title', 'company', 'url', name='uix_opportunity_title_company_url'),
    )
