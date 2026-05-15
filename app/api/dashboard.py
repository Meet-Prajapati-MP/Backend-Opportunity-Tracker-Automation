from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.compat import DashboardStatsResponse
from app.db.database import get_db
from app.services.opportunity_service import OpportunityService
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_opportunity_service(db: AsyncSession = Depends(get_db)) -> OpportunityService:
    return OpportunityService(db)


def get_tracking_service(db: AsyncSession = Depends(get_db)) -> TrackingService:
    return TrackingService(db)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    opportunity_service: OpportunityService = Depends(get_opportunity_service),
    tracking_service: TrackingService = Depends(get_tracking_service),
):
    opportunities = await opportunity_service.get_all(skip=0, limit=1000)
    tracking_items = await tracking_service.get_all(skip=0, limit=1000)

    today = datetime.now(timezone.utc).date()
    next_week = today + timedelta(days=7)

    return {
        "total_opportunities": len(opportunities),
        "new_today": sum(1 for item in opportunities if getattr(item, "created_at", None) and item.created_at.date() == today),
        "tracked": len(tracking_items),
        "applied": sum(1 for item in tracking_items if (item.status or "").lower() == "applied"),
        "deadlines_this_week": sum(
            1
            for item in opportunities
            if getattr(item, "posted_date", None) and today <= item.posted_date <= next_week
        ),
    }