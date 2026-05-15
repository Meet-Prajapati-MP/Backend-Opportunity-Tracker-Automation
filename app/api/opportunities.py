from math import ceil
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.compat import PaginatedFrontendOpportunityResponse, serialize_opportunity
from app.db.database import get_db
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

def get_opportunity_service(db: AsyncSession = Depends(get_db)) -> OpportunityService:
    return OpportunityService(db)

@router.get("", response_model=PaginatedFrontendOpportunityResponse)
async def get_opportunities(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(12, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search query"),
    status: Optional[str] = Query(None, description="Status filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    items = await service.get_all(skip=0, limit=1000)

    def matches(item) -> bool:
        serialized = serialize_opportunity(item)

        if search:
            haystack = " ".join(
                [serialized["title"], serialized["organization"], serialized["description"], serialized["source"]]
            ).lower()
            if search.lower() not in haystack:
                return False

        if status and status != "all" and serialized["status"] != status:
            return False

        if category and category != "all" and serialized["category"] != category:
            return False

        return True

    filtered = [item for item in items if matches(item)]
    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    page_items = filtered[start:end]

    return {
        "items": [serialize_opportunity(item) for item in page_items],
        "total": total,
        "page": page,
        "size": size,
        "pages": max(ceil(total / size), 1) if total else 1,
    }

@router.get("/search")
async def search_opportunities(
    keyword: Optional[str] = Query(None, alias="q", description="Search keyword"),
    country: Optional[str] = Query(None, description="Country filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    tags: Optional[str] = Query(None, description="Tags filter (comma-separated)"),
    deadline: Optional[str] = Query(None, description="Deadline filter"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    items = await service.get_all(skip=0, limit=1000)
    if not keyword:
        return [serialize_opportunity(item) for item in items]

    term = keyword.lower()
    results = []
    for item in items:
        serialized = serialize_opportunity(item)
        haystack = " ".join(
            [serialized["title"], serialized["organization"], serialized["description"], serialized["source"]]
        ).lower()
        if term in haystack:
            results.append(serialized)

    return results

@router.get("/latest")
async def get_latest_opportunities(
    limit: int = Query(10, ge=1, le=100, description="Number of latest opportunities to retrieve"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    items = await service.get_all(skip=0, limit=1000)
    items = sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]
    return [serialize_opportunity(item) for item in items]

@router.get("/expiring-soon")
async def get_expiring_soon_opportunities(
    limit: int = Query(10, ge=1, le=100, description="Number of expiring opportunities to retrieve"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    return []

@router.get("/{id}")
async def get_opportunity(
    id: UUID,
    service: OpportunityService = Depends(get_opportunity_service)
):
    opportunity = await service.get_by_id(id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return serialize_opportunity(opportunity)
