import json
from typing import List, Dict, Any
from app.scrapers.base_scraper import BaseScraper

class YouthOpportunitiesScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "Youth Opportunities"

    async def extract_opportunities(self, html: str) -> List[Dict[str, Any]]:
        soup = self.parse_html(html)
        results = []
        seen_urls = set()

        # Youth Opportunities usually uses grid layouts with 'opportunity-item', 'item', or 'post' classes
        for item in soup.find_all(["div", "article"], class_=["opportunity-item", "item", "post", "type-post"]):
            # Target common heading hierarchies or direct links
            title_tag = item.find(["h2", "h3", "h4", "a"], class_=["title", "entry-title"])
            if not title_tag:
                continue

            # Handle case where the title itself is the <a> tag, or contains the <a> tag
            link_tag = title_tag if title_tag.name == "a" else title_tag.find("a")
            if not link_tag:
                continue

            source_url = link_tag.get("href")
            
            # Duplicate prevention mechanism
            if not source_url or source_url in seen_urls:
                continue
            seen_urls.add(source_url)

            title = title_tag.get_text(strip=True)
            desc_tag = item.find(class_=["description", "excerpt", "entry-summary", "post-content"])
            description = desc_tag.get_text(strip=True) if desc_tag else None

            # Attempt to extract deadline from common meta wrappers
            meta_div = item.find(class_=["meta", "post-meta", "opportunity-meta"])
            deadline = None
            if meta_div:
                deadline_tag = meta_div.find(class_=["deadline", "date", "time"])
                if deadline_tag:
                    deadline = deadline_tag.get_text(strip=True)

            cat_links = item.find(class_=["category", "tags", "cat-links"])
            tags = [a.get_text(strip=True) for a in cat_links.find_all("a")] if cat_links else []

            results.append({
                "title": title,
                "organization": "Unknown", 
                "country": "Global",       
                "deadline": deadline,          
                "description": description,
                "source_url": source_url,
                "tags": tags
            })

        return results

    async def get_normalized_json(self, start_url: str) -> str:
        """Fetches, extracts, and returns the strictly normalized JSON array."""
        raw_data = await self.scrape(start_url)
        return json.dumps(raw_data, indent=2, ensure_ascii=False)
