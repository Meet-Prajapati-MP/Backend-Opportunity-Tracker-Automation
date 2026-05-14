from typing import Optional
from pydantic import BaseModel
from app.ai.extractor import BaseAIAgent

class CategoryResult(BaseModel):
    primary_category: str
    confidence_score: float
    is_remote_eligible: bool
    target_audience: list[str]

class OpportunityCategorizer(BaseAIAgent):
    """Categorizes an opportunity based on its structured details."""
    
    async def categorize(self, title: str, description: str) -> Optional[CategoryResult]:
        prompt = f"""
        Analyze the following opportunity and categorize it.
        Title: {title}
        Description: {description}
        
        Provide the primary category (e.g., 'Scholarship', 'Job', 'Grant', 'Fellowship'), 
        confidence score (0.0 to 1.0), whether it's remote eligible, and target audience (e.g., 'students', 'professionals').
        """
        return await self.generate(prompt, CategoryResult)
