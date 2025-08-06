"""SERP data models."""

from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC


class SearchRequest(BaseModel):
    """Search request model for Bright Data SERP API."""
    
    query: str = Field(..., description="Search query string", min_length=1)
    country: str = Field(default="US", description="Country code for search (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code for search (ISO 639-1)")
    page: int = Field(default=1, description="Page number for pagination", ge=1)
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country code format."""
        if len(v) != 2 or not v.isupper():
            raise ValueError('Country code must be 2-letter uppercase ISO code')
        return v
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code format."""
        if len(v) != 2 or not v.islower():
            raise ValueError('Language code must be 2-letter lowercase ISO code')
        return v


class SearchResult(BaseModel):
    """Individual search result model."""
    
    rank: int = Field(..., description="Result rank/position in SERP", ge=1)
    title: str = Field(..., description="Result title")
    url: HttpUrl = Field(..., description="Result URL")
    description: Optional[str] = Field(None, description="Result snippet/description")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rank": 1,
                "title": "Example Title",
                "url": "https://example.com",
                "description": "Example description snippet"
            }
        }
    )


class SearchResponse(BaseModel):
    """Complete search response model."""
    
    query: str = Field(..., description="Original search query")
    results_count: int = Field(..., description="Number of results returned", ge=0)
    organic_results: List[SearchResult] = Field(default=[], description="Organic search results")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Response timestamp")
    search_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional search metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "pizza",
                "results_count": 10,
                "organic_results": [
                    {
                        "rank": 1,
                        "title": "Best Pizza Near Me",
                        "url": "https://example.com/pizza",
                        "description": "Find the best pizza restaurants in your area"
                    }
                ],
                "search_metadata": {
                    "search_time": 0.45,
                    "country": "US",
                    "language": "en"
                }
            }
        }
    )


# Legacy model aliases for backward compatibility
SearchQuery = SearchRequest
SerpResult = SearchResult
SerpResponse = SearchResponse