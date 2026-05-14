from typing import Optional, List
from pydantic import BaseModel
from app.ai.extractor import BaseAIAgent

class SearchIntent(BaseModel):
    keywords: List[str]
    location: Optional[str] = None
    job_type: Optional[str] = None
    organization_type: Optional[str] = None

class NaturalLanguageSearchParser(BaseAIAgent):
    """Parses natural language search queries into structured database query parameters."""
    
    async def parse_query(self, query: str) -> Optional[SearchIntent]:
        prompt = f"""
        Extract search parameters from the user's natural language query.
        Query: "{query}"
        
        Extract keywords (list of main search terms), location (if any), job_type (if any), and organization_type (if any).
        """
        return await self.generate(prompt, SearchIntent)
