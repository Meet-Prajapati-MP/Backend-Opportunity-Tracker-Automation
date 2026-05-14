"""
Daily ingestion pipeline.

Flow per scraper:
  1. Scrape raw opportunities
  2. Deduplicate by URL (in-memory + DB check via service)
  3. Run AI extraction on each item's description
  4. Run AI categorization on extracted data
  5. Persist via OpportunityService (idempotent create)
  6. Log execution with status + metrics
  7. Isolate per-item failures so one bad record never aborts the run
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.ai.categorizer import CategoryResult, OpportunityCategorizer
from app.ai.extractor import ExtractedOpportunity, OpportunityExtractor
from app.db.database import AsyncSessionLocal
from app.schemas.opportunity import OpportunityCreate
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.opportunity_desk import OpportunityDeskScraper
from app.scrapers.youth_opportunities import YouthOpportunitiesScraper
from app.services.opportunity_service import OpportunityService
from app.services.scraper_service import ScraperService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scraper registry — add new scrapers here only
# ---------------------------------------------------------------------------
SCRAPER_REGISTRY: list[tuple[BaseScraper, str]] = [
    (OpportunityDeskScraper(), "https://opportunitydesk.org/"),
    (YouthOpportunitiesScraper(), "https://youthop.com/"),
]

# ---------------------------------------------------------------------------
# Result dataclass for structured per-run reporting
# ---------------------------------------------------------------------------
@dataclass
class PipelineResult:
    source: str
    scraped: int = 0
    saved: int = 0
    ai_extracted: int = 0
    ai_categorized: int = 0
    failed_items: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AI helpers
# ---------------------------------------------------------------------------
async def _run_extraction(extractor: OpportunityExtractor, raw_text: str) -> Optional[ExtractedOpportunity]:
    """Run AI extraction with failure isolation."""
    try:
        return await extractor.extract(raw_text)
    except Exception as e:
        logger.warning(f"AI extraction failed: {e}")
        return None


async def _run_categorization(
    categorizer: OpportunityCategorizer, title: str, description: str
) -> Optional[CategoryResult]:
    """Run AI categorization with failure isolation."""
    try:
        return await categorizer.categorize(title, description)
    except Exception as e:
        logger.warning(f"AI categorization failed for '{title}': {e}")
        return None


# ---------------------------------------------------------------------------
# Per-item processing
# ---------------------------------------------------------------------------
async def _process_item(
    raw: dict,
    seen_urls: set[str],
    opp_service: OpportunityService,
    extractor: OpportunityExtractor,
    categorizer: OpportunityCategorizer,
    result: PipelineResult,
) -> None:
    """
    Process a single scraped item end-to-end.
    All exceptions are caught so one bad item never aborts the run.
    """
    url = raw.get("source_url") or raw.get("url", "")
    if not url or url in seen_urls:
        return  # in-memory dedup before hitting the DB
    seen_urls.add(url)

    try:
        raw_description = raw.get("description") or ""
        title = raw.get("title", "Unknown")

        # --- AI Extraction ---
        extracted: Optional[ExtractedOpportunity] = None
        if raw_description:
            extracted = await _run_extraction(extractor, raw_description)
            if extracted:
                result.ai_extracted += 1

        # --- AI Categorization ---
        category: Optional[CategoryResult] = None
        if extracted:
            category = await _run_categorization(
                categorizer, extracted.title, extracted.description_summary
            )
            if category:
                result.ai_categorized += 1

        # --- Build OpportunityCreate merging raw + AI-extracted fields ---
        opp_in = OpportunityCreate(
            title=extracted.title if extracted else title,
            company=extracted.organization if extracted else raw.get("organization", "Unknown"),
            url=url,
            location=extracted.country if extracted else raw.get("country"),
            description=extracted.description_summary if extracted else raw_description[:2000] or None,
            salary_range=extracted.salary_range if extracted else None,
            source=raw.get("source", result.source),
        )

        # --- Persist (idempotent: service returns existing on duplicate URL) ---
        saved = await opp_service.create(opp_in)
        if saved:
            result.saved += 1

    except Exception as e:
        result.failed_items += 1
        result.errors.append(f"[{url}] {type(e).__name__}: {e}")
        logger.exception(f"Unhandled error processing item '{url}': {e}")


# ---------------------------------------------------------------------------
# Per-scraper pipeline
# ---------------------------------------------------------------------------
async def _run_scraper_pipeline(
    scraper: BaseScraper,
    start_url: str,
    extractor: OpportunityExtractor,
    categorizer: OpportunityCategorizer,
) -> PipelineResult:
    """
    Full pipeline for a single scraper source.
    Scraper execution failure is isolated from other scrapers.
    """
    result = PipelineResult(source=scraper.source_name)

    async with AsyncSessionLocal() as session:
        opp_service = OpportunityService(session)
        scraper_service = ScraperService(session, opp_service)

        try:
            raw_items: list[dict] = await scraper_service.run_scraper(scraper, start_url)
            # run_scraper returns a status dict, not items — re-scrape for item-level processing
            raw_items = await scraper.scrape(start_url)
            result.scraped = len(raw_items)
            logger.info(f"[{scraper.source_name}] Scraped {result.scraped} raw items.")

        except Exception as e:
            logger.exception(f"[{scraper.source_name}] Scraping failed: {e}")
            result.errors.append(f"Scrape error: {e}")
            return result

        seen_urls: set[str] = set()
        tasks = [
            _process_item(raw, seen_urls, opp_service, extractor, categorizer, result)
            for raw in raw_items
        ]
        # Process items concurrently but bounded to avoid overwhelming AI APIs
        semaphore = asyncio.Semaphore(5)

        async def bounded(task):
            async with semaphore:
                await task

        await asyncio.gather(*[bounded(t) for t in tasks], return_exceptions=True)

    return result


# ---------------------------------------------------------------------------
# Main pipeline entrypoint
# ---------------------------------------------------------------------------
async def run_daily_pipeline() -> None:
    """
    Orchestrates the full daily ingestion pipeline across all registered scrapers.
    Each scraper runs independently; failure of one does not affect others.
    """
    logger.info("=== Daily pipeline started ===")

    # Shared AI clients (one instance per run to reuse connections)
    extractor = OpportunityExtractor(provider="openai", model="gpt-4o-mini")
    categorizer = OpportunityCategorizer(provider="openai", model="gpt-4o-mini")

    results: list[PipelineResult] = []

    for scraper, start_url in SCRAPER_REGISTRY:
        logger.info(f"[{scraper.source_name}] Starting pipeline...")
        try:
            result = await _run_scraper_pipeline(scraper, start_url, extractor, categorizer)
            results.append(result)
        except Exception as e:
            # Last-resort isolation: if the entire scraper block crashes, log and continue
            logger.exception(f"[{scraper.source_name}] Pipeline block crashed: {e}")
            results.append(PipelineResult(source=scraper.source_name, errors=[str(e)]))

    # --- Summary logging ---
    logger.info("=== Daily pipeline complete ===")
    for r in results:
        logger.info(
            f"  [{r.source}] scraped={r.scraped} saved={r.saved} "
            f"ai_extracted={r.ai_extracted} ai_categorized={r.ai_categorized} "
            f"failed_items={r.failed_items} errors={len(r.errors)}"
        )
        for err in r.errors:
            logger.warning(f"    └─ {err}")


# ---------------------------------------------------------------------------
# APScheduler factory
# ---------------------------------------------------------------------------
def create_scheduler() -> AsyncIOScheduler:
    """
    Creates and configures the APScheduler instance.
    Call scheduler.start() / scheduler.shutdown() inside the app lifespan.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=2, minute=0),  # 02:00 UTC daily
        id="daily_pipeline",
        name="Daily Opportunity Ingestion",
        replace_existing=True,
        max_instances=1,          # Prevent overlapping runs
        misfire_grace_time=3600,  # Allow up to 1h late start after downtime
    )
    return scheduler
