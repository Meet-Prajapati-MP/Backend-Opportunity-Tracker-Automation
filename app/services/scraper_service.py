import logging
import time
from typing import List, Dict, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log import ScraperLog
from app.schemas.opportunity import OpportunityCreate
from app.schemas.log import ScraperLogCreate
from app.services.opportunity_service import OpportunityService
from app.scrapers.base_scraper import BaseScraper
from typing import Optional, Any

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, db: AsyncSession, opportunity_service: Optional[OpportunityService] = None):
        self.db = db
        self.opportunity_service = opportunity_service or OpportunityService(db)

    async def _log_run(self, source: str, status: str, records_found: int, error_msg: Optional[str] = None, exec_time: Optional[int] = None) -> ScraperLog:
        """Helper to create transaction-safe tracking logs for scraper execution."""
        log_data = ScraperLogCreate(
            source=source,
            status=status,
            records_found=records_found,
            error_message=error_msg,
            execution_time_ms=exec_time
        )
        log_entry = ScraperLog(**log_data.model_dump())
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def run_scraper(self, scraper: BaseScraper, start_url: str) -> Dict[str, Any]:
        """Orchestrates pulling data from an external source and persisting it safely."""
        source = scraper.source_name
        logger.info(f"Initiating scraper run for {source}")
        start_time = time.time()
        
        try:
            # 1. Execute remote scraping logic
            scraped_data = await scraper.scrape(start_url)
            
            # 2. Iterate and persist, filtering duplicates natively via the OpportunityService
            saved_count = 0
            for item in scraped_data:
                # Handle either dicts or pydantic objects seamlessly based on scraper output format
                data_dict = item if isinstance(item, dict) else item.model_dump()
                
                opp_in = OpportunityCreate(
                    title=data_dict.get("title", "Unknown"),
                    company=data_dict.get("organization", data_dict.get("company", "Unknown")),
                    url=data_dict.get("source_url", data_dict.get("url", "")),
                    location=data_dict.get("country", data_dict.get("location")),
                    description=data_dict.get("description"),
                    source=source
                )
                
                # Service layer gracefully catches UniqueConstraints
                created = await self.opportunity_service.create(opp_in)
                if created:
                    saved_count += 1
            
            # 3. Log success
            exec_time_ms = int((time.time() - start_time) * 1000)
            await self._log_run(source, "success", saved_count, None, exec_time_ms)
            
            return {
                "status": "success",
                "source": source,
                "scraped_total": len(scraped_data),
                "saved_new": saved_count,
                "execution_time_ms": exec_time_ms
            }
            
        except Exception as e:
            # Rollbacks triggered gracefully by underlying services or connection pooling
            logger.exception(f"Scraper run failed completely for {source}")
            exec_time_ms = int((time.time() - start_time) * 1000)
            await self._log_run(source, "failed", 0, str(e), exec_time_ms)
            return {"status": "error", "message": str(e)}
