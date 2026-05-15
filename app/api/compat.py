from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationTracking as ApplicationTrackingModel
from app.models.opportunity import Opportunity as OpportunityModel


class FrontendOpportunity(BaseModel):
    id: str
    title: str
    organization: str
    description: str
    category: str
    tags: list[str]
    deadline: str | None
    url: str
    source: str
    status: str
    ai_score: float | None
    ai_summary: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class FrontendTrackedOpportunity(BaseModel):
    id: str
    opportunity_id: str
    opportunity: FrontendOpportunity
    status: str
    notes: str | None
    applied_at: str | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedFrontendOpportunityResponse(BaseModel):
    items: list[FrontendOpportunity]
    total: int
    page: int
    size: int
    pages: int


class DashboardStatsResponse(BaseModel):
    total_opportunities: int
    new_today: int
    tracked: int
    applied: int
    deadlines_this_week: int


class AiSearchResponse(BaseModel):
    opportunities: list[FrontendOpportunity]
    query: str
    total: int
    ai_explanation: str | None = None


def _iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value.isoformat()


def map_tracking_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"planning", "saved"}:
        return "saved"
    if normalized in {"interview", "applied"}:
        return "applied"
    if normalized in {"accepted"}:
        return "accepted"
    if normalized in {"rejected"}:
        return "rejected"
    if normalized in {"waitlisted"}:
        return "saved"
    return "new"


def serialize_opportunity(opportunity: OpportunityModel) -> dict[str, Any]:
    applications = list(getattr(opportunity, "applications", []) or [])
    status = "new"

    if applications:
        latest_application = applications[0]
        status = map_tracking_status(getattr(latest_application, "status", None))

    return {
        "id": str(opportunity.id),
        "title": opportunity.title,
        "organization": opportunity.company,
        "description": opportunity.description or "",
        "category": opportunity.source or "General",
        "tags": [],
        "deadline": _iso(opportunity.posted_date),
        "url": opportunity.url,
        "source": opportunity.source or "Unknown",
        "status": status,
        "ai_score": None,
        "ai_summary": None,
        "created_at": _iso(opportunity.created_at) or "",
        "updated_at": _iso(opportunity.updated_at) or "",
    }


def serialize_tracking(record: ApplicationTrackingModel) -> dict[str, Any]:
    opportunity = getattr(record, "opportunity", None)
    return {
        "id": str(record.id),
        "opportunity_id": str(record.opportunity_id),
        "opportunity": serialize_opportunity(opportunity) if opportunity else {
            "id": str(record.opportunity_id),
            "title": "Unknown opportunity",
            "organization": "Unknown",
            "description": "",
            "category": "General",
            "tags": [],
            "deadline": None,
            "url": "",
            "source": "Unknown",
            "status": map_tracking_status(record.status),
            "ai_score": None,
            "ai_summary": None,
            "created_at": _iso(record.created_at) or "",
            "updated_at": _iso(record.updated_at) or "",
        },
        "status": map_tracking_status(record.status),
        "notes": record.notes,
        "applied_at": _iso(record.applied_date),
        "created_at": _iso(record.created_at) or "",
    }
