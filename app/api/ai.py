from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.compat import AiSearchResponse, serialize_opportunity
from app.db.database import get_db
from app.services.opportunity_service import OpportunityService

router = APIRouter(prefix="/ai", tags=["ai"])


class AiSearchRequest(BaseModel):
    query: str


def get_opportunity_service(db: AsyncSession = Depends(get_db)) -> OpportunityService:
    return OpportunityService(db)


@router.post("/search", response_model=AiSearchResponse)
async def search_ai(
    payload: AiSearchRequest,
    service: OpportunityService = Depends(get_opportunity_service),
):
    items = await service.get_all(skip=0, limit=1000)
    query = payload.query.strip()

    if not query:
        return {"opportunities": [], "query": payload.query, "total": 0, "ai_explanation": "Enter a query to search opportunities."}

    terms = [term for term in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(term) > 1]
    scored: list[tuple[int, dict]] = []

    for item in items:
        serialized = serialize_opportunity(item)
        haystack = " ".join(
            [serialized["title"], serialized["organization"], serialized["description"], serialized["category"], serialized["source"]]
        ).lower()
        score = sum(1 for term in terms if term in haystack)
        if score > 0:
            scored.append((score, serialized))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [item for _, item in scored]

    explanation = f"Found {len(results)} opportunities matching {len(terms) or 1} search terms." if results else "No opportunities matched this query."

    return {
        "opportunities": results,
        "query": payload.query,
        "total": len(results),
        "ai_explanation": explanation,
    }