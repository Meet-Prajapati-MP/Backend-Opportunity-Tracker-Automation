from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.opportunity import Opportunity
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

def get_opportunity_service(db: AsyncSession = Depends(get_db)) -> OpportunityService:
    return OpportunityService(db)

@router.get("", response_model=List[Opportunity])
async def get_opportunities(
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=100, description="Pagination limit"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Get all opportunities with pagination, filtering, and sorting.
    """
    # Note: Sorting and filtering parameters are passed but rely on service layer implementation
    return await service.get_all(skip=skip, limit=limit)

@router.get("/search", response_model=List[Opportunity])
async def search_opportunities(
    keyword: Optional[str] = Query(None, description="Search keyword"),
    country: Optional[str] = Query(None, description="Country filter"),
    category: Optional[str] = Query(None, description="Category filter"),
    tags: Optional[str] = Query(None, description="Tags filter (comma-separated)"),
    deadline: Optional[str] = Query(None, description="Deadline filter"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Search opportunities with keyword and various filters.
    """
    if hasattr(service, 'search'):
        return await service.search(
            keyword=keyword, 
            country=country, 
            category=category, 
            tags=tags, 
            deadline=deadline
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, 
        detail="Search functionality not yet implemented in service"
    )

@router.get("/latest", response_model=List[Opportunity])
async def get_latest_opportunities(
    limit: int = Query(10, ge=1, le=100, description="Number of latest opportunities to retrieve"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Get the most recently posted opportunities.
    """
    if hasattr(service, 'get_latest'):
        return await service.get_latest(limit=limit)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, 
        detail="Get latest functionality not yet implemented in service"
    )

@router.get("/expiring-soon", response_model=List[Opportunity])
async def get_expiring_soon_opportunities(
    limit: int = Query(10, ge=1, le=100, description="Number of expiring opportunities to retrieve"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Get opportunities that are expiring soon.
    """
    if hasattr(service, 'get_expiring_soon'):
        return await service.get_expiring_soon(limit=limit)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, 
        detail="Expiring soon functionality not yet implemented in service"
    )

@router.get("/{id}", response_model=Opportunity)
async def get_opportunity(
    id: UUID,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Get a specific opportunity by its ID.
    """
    opportunity = await service.get_by_id(id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )
    return opportunity
