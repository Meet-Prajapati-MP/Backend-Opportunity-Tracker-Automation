import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.models.opportunity import Opportunity
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate

logger = logging.getLogger(__name__)

class OpportunityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, opp_id: UUID) -> Optional[Opportunity]:
        result = await self.db.execute(
            select(Opportunity)
            .options(selectinload(Opportunity.applications))
            .where(Opportunity.id == opp_id)
        )
        return result.scalars().first()

    async def get_by_url(self, url: str) -> Optional[Opportunity]:
        result = await self.db.execute(
            select(Opportunity)
            .options(selectinload(Opportunity.applications))
            .where(Opportunity.url == url)
        )
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Opportunity]:
        result = await self.db.execute(
            select(Opportunity)
            .options(selectinload(Opportunity.applications))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj_in: OpportunityCreate) -> Optional[Opportunity]:
        # Graceful duplicate handling using URL as unique identifier
        existing = await self.get_by_url(obj_in.url)
        if existing:
            logger.info(f"Opportunity with URL {obj_in.url} already exists. Skipping creation.")
            return existing

        db_obj = Opportunity(**obj_in.model_dump())
        self.db.add(db_obj)
        try:
            await self.db.commit()
            await self.db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error creating opportunity {obj_in.title}: {e}")
            return None

    async def update(self, opp_id: UUID, obj_in: OpportunityUpdate) -> Optional[Opportunity]:
        db_obj = await self.get_by_id(opp_id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, opp_id: UUID) -> bool:
        db_obj = await self.get_by_id(opp_id)
        if not db_obj:
            return False
            
        await self.db.delete(db_obj)
        await self.db.commit()
        return True
