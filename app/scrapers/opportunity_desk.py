import json
from typing import List, Dict, Any
from app.scrapers.base_scraper import BaseScraper

class OpportunityDeskScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "Opportunity Desk"

    async def extract_opportunities(self, html: str) -> List[Dict[str, Any]]:
        soup = self.parse_html(html)
        results = []
        seen_urls = set()

        for article in soup.find_all(["article", "div"], class_=["post", "type-post"]):
            title_tag = article.find(["h2", "h3"])
            if not title_tag or not title_tag.find("a"):
                continue

            link_tag = title_tag.find("a")
            source_url = link_tag.get("href")
            
            if not source_url or source_url in seen_urls:
                continue
            seen_urls.add(source_url)

            title = title_tag.get_text(strip=True)
            desc_tag = article.find(class_="entry-content") or article.find(class_="post-content")
            description = desc_tag.get_text(strip=True) if desc_tag else None

            cat_links = article.find(class_="cat-links")
            tags = [a.get_text(strip=True) for a in cat_links.find_all("a")] if cat_links else []

            results.append({
                "title": title,
                "organization": "Unknown", 
                "country": "Global",       
                "deadline": None,          
                "description": description,
                "source_url": source_url,
                "tags": tags
            })

        return results

    async def get_normalized_json(self, start_url: str) -> str:
        """Fetches, extracts, and returns the strictly normalized JSON array."""
        # Intentionally overriding the return type of the base orchestration method for JSON
        raw_data = await self.scrape(start_url)
        return json.dumps(raw_data, indent=2, ensure_ascii=False)
