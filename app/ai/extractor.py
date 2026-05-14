import json
import asyncio
import logging
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseAIAgent:
    """Reusable async base for interacting with LLM providers enforcing JSON structure."""
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini", max_retries: int = 3):
        self.provider = provider.lower()
        self.model = model
        self.max_retries = max_retries
        
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "gemini":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(self.model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _call_openai(self, prompt: str, schema: Type[T]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a strict data extraction assistant. You must respond ONLY with valid JSON matching this JSON schema: {schema.model_json_schema()}"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    async def _call_gemini(self, prompt: str, schema: Type[T]) -> str:
        # Run synchronous gemini call in thread pool to maintain async behavior
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.gemini_model.generate_content(
                f"You are a strict data extraction assistant. Respond ONLY with valid JSON matching this schema: {schema.model_json_schema()}\n\nInput: {prompt}",
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
        )
        return response.text

    async def generate(self, prompt: str, schema: Type[T]) -> Optional[T]:
        """Orchestrates generation with automatic retries and Pydantic validation."""
        for attempt in range(self.max_retries):
            try:
                if self.provider == "openai":
                    result_text = await self._call_openai(prompt, schema)
                else:
                    result_text = await self._call_gemini(prompt, schema)
                
                parsed_data = json.loads(result_text)
                return schema(**parsed_data)
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} parsing failed: {e}")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{self.max_retries} API error: {e}")
                
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
        logger.error("Max retries reached for AI generation")
        return None

class ExtractedOpportunity(BaseModel):
    title: str
    organization: str
    country: Optional[str] = None
    deadline: Optional[str] = None
    description_summary: str
    salary_range: Optional[str] = None
    tags: list[str] = []

class OpportunityExtractor(BaseAIAgent):
    """Extracts structured fields from raw scraped opportunity descriptions."""
    
    async def extract(self, raw_text: str) -> Optional[ExtractedOpportunity]:
        prompt = f"Extract the key details from the following opportunity description:\n\n{raw_text}"
        return await self.generate(prompt, ExtractedOpportunity)
