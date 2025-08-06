"""SERP data models."""

from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC


class SearchRequest(BaseModel):
    """Search request model for Bright Data SERP API."""
    
    query: str = Field(..., description="Search query string", min_length=1)
    country: str = Field(default="US", description="Country code for search (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code for search (ISO 639-1)")
    page: int = Field(default=1, description="Page number for pagination", ge=1, le=100)
    results_per_page: int = Field(default=10, description="Results per page", ge=1, le=100)
    
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


class PaginationMetadata(BaseModel):
    """Pagination metadata model."""
    
    current_page: int = Field(..., description="Current page number", ge=1)
    results_per_page: int = Field(..., description="Results per page", ge=1)
    total_results_estimate: Optional[int] = Field(None, description="Estimated total results from Google")
    total_pages_estimate: Optional[int] = Field(None, description="Estimated total pages available")
    has_next_page: bool = Field(..., description="Whether there are more pages available")
    has_previous_page: bool = Field(..., description="Whether there are previous pages")
    page_range_start: int = Field(..., description="First result number on this page", ge=1)
    page_range_end: int = Field(..., description="Last result number on this page", ge=1)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_page": 1,
                "results_per_page": 10,
                "total_results_estimate": 45600000,
                "total_pages_estimate": 4560000,
                "has_next_page": True,
                "has_previous_page": False,
                "page_range_start": 1,
                "page_range_end": 10
            }
        }
    )


class SearchResponse(BaseModel):
    """Complete search response model."""
    
    query: str = Field(..., description="Original search query")
    results_count: int = Field(..., description="Number of results returned", ge=0)
    organic_results: List[SearchResult] = Field(default=[], description="Organic search results")
    pagination: Optional[PaginationMetadata] = Field(None, description="Pagination metadata")
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
                "pagination": {
                    "current_page": 1,
                    "results_per_page": 10,
                    "total_results_estimate": 45600000,
                    "total_pages_estimate": 4560000,
                    "has_next_page": True,
                    "has_previous_page": False,
                    "page_range_start": 1,
                    "page_range_end": 10
                },
                "search_metadata": {
                    "search_time": 0.45,
                    "country": "US",
                    "language": "en"
                }
            }
        }
    )


class BatchPaginationRequest(BaseModel):
    """Request model for batch pagination searches."""
    
    query: str = Field(..., description="Search query string", min_length=1)
    country: str = Field(default="US", description="Country code for search (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code for search (ISO 639-1)")
    max_pages: int = Field(default=3, description="Maximum pages to fetch", ge=1, le=10)
    results_per_page: int = Field(default=10, description="Results per page", ge=1, le=100)
    start_page: int = Field(default=1, description="Starting page number", ge=1)
    
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


class PageResult(BaseModel):
    """Individual page result in batch pagination response."""
    
    page_number: int = Field(..., description="Page number", ge=1)
    results_count: int = Field(..., description="Number of results on this page", ge=0)
    organic_results: List[SearchResult] = Field(default=[], description="Organic search results for this page")
    pagination: Optional[PaginationMetadata] = Field(None, description="Pagination metadata for this page")
    search_metadata: Optional[Dict[str, Any]] = Field(None, description="Search metadata for this page")


class BatchPaginationSummary(BaseModel):
    """Summary metadata for batch pagination response."""
    
    total_results_estimate: Optional[int] = Field(None, description="Estimated total results across all pages")
    results_per_page: int = Field(..., description="Results per page requested")
    pages_requested: int = Field(..., description="Number of pages requested")
    pages_fetched: int = Field(..., description="Number of pages successfully fetched")
    start_page: int = Field(..., description="Starting page number")
    end_page: int = Field(..., description="Ending page number")
    batch_processing_time: Optional[float] = Field(None, description="Total time to process batch request")


class BatchPaginationResponse(BaseModel):
    """Response model for batch pagination searches."""
    
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total results across all fetched pages", ge=0)
    pages_fetched: int = Field(..., description="Number of pages successfully fetched", ge=0)
    pagination_summary: BatchPaginationSummary = Field(..., description="Batch pagination summary")
    pages: List[PageResult] = Field(default=[], description="Results for each fetched page")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Response timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "python programming",
                "total_results": 30,
                "pages_fetched": 3,
                "pagination_summary": {
                    "total_results_estimate": 45600000,
                    "results_per_page": 10,
                    "pages_requested": 3,
                    "pages_fetched": 3,
                    "start_page": 1,
                    "end_page": 3,
                    "batch_processing_time": 4.25
                },
                "pages": [
                    {
                        "page_number": 1,
                        "results_count": 10,
                        "organic_results": [],
                        "pagination": {
                            "current_page": 1,
                            "results_per_page": 10,
                            "has_next_page": True,
                            "has_previous_page": False,
                            "page_range_start": 1,
                            "page_range_end": 10
                        }
                    }
                ]
            }
        }
    )


# Legacy model aliases for backward compatibility
SearchQuery = SearchRequest
SerpResult = SearchResult
SerpResponse = SearchResponse