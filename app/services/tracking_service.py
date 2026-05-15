import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.application import ApplicationTracking
from app.schemas.application import ApplicationTrackingCreate, ApplicationTrackingUpdate

logger = logging.getLogger(__name__)

class TrackingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tracking_id: UUID) -> Optional[ApplicationTracking]:
        result = await self.db.execute(
            select(ApplicationTracking)
            .options(selectinload(ApplicationTracking.opportunity))
            .where(ApplicationTracking.id == tracking_id)
        )
        return result.scalars().first()

    async def get_by_opportunity(self, opportunity_id: UUID) -> Optional[ApplicationTracking]:
        result = await self.db.execute(
            select(ApplicationTracking)
            .options(selectinload(ApplicationTracking.opportunity))
            .where(ApplicationTracking.opportunity_id == opportunity_id)
        )
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ApplicationTracking]:
        result = await self.db.execute(
            select(ApplicationTracking)
            .options(selectinload(ApplicationTracking.opportunity))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj_in: ApplicationTrackingCreate) -> ApplicationTracking:
        # Prevent tracking duplication on the same opportunity
        existing = await self.get_by_opportunity(obj_in.opportunity_id)
        if existing:
            logger.info(f"Tracking record for opportunity {obj_in.opportunity_id} already exists. Returning existing.")
            return existing

        db_obj = ApplicationTracking(**obj_in.model_dump())
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, tracking_id: UUID, obj_in: ApplicationTrackingUpdate) -> Optional[ApplicationTracking]:
        db_obj = await self.get_by_id(tracking_id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
