import abc
import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ScrapedOpportunity(BaseModel):
    """Structured output format for all scrapers."""
    title: str
    company: str
    url: str
    location: Optional[str] = None
    description: Optional[str] = None
    salary_range: Optional[str] = None
    source: str

class BaseScraper(abc.ABC):
    """Abstract base class for all opportunity scrapers."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Name of the source being scraped (e.g., 'LinkedIn', 'Indeed')."""
        pass

    async def fetch_page(self, url: str, client: httpx.AsyncClient) -> Optional[str]:
        """Fetch a page with retry and timeout logic."""
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(f"[{self.source_name}] Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"[{self.source_name}] Max retries reached for {url}")
                    return None

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object."""
        return BeautifulSoup(html_content, 'html.parser')

    @abc.abstractmethod
    async def extract_opportunities(self, html: str) -> List[ScrapedOpportunity]:
        """Abstract method to extract structured data from raw HTML."""
        pass

    async def scrape(self, start_url: str) -> List[ScrapedOpportunity]:
        """Main orchestrated scraping workflow."""
        logger.info(f"Starting scrape for {self.source_name} at {start_url}")
        
        # httpx AsyncClient context manager handles connection pooling properly
        async with httpx.AsyncClient() as client:
            html_content = await self.fetch_page(start_url, client)
            if not html_content:
                logger.error(f"Failed to retrieve content for {self.source_name}")
                return []
                
            try:
                results = await self.extract_opportunities(html_content)
                logger.info(f"Successfully scraped {len(results)} opportunities from {self.source_name}")
                return results
            except Exception as e:
                logger.exception(f"Error extracting opportunities for {self.source_name}: {e}")
                return []
