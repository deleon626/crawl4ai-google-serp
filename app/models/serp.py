"""SERP data models."""

from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from enum import Enum


class SocialPlatform(str, Enum):
    """Social media platform filtering options."""
    
    NONE = "none"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"


class InstagramContentType(str, Enum):
    """Instagram content type filtering options."""
    
    ALL = "all"
    REELS = "reels"
    POSTS = "posts"  
    ACCOUNTS = "accounts"
    TV = "tv"
    LOCATIONS = "locations"


class LinkedInContentType(str, Enum):
    """LinkedIn content type filtering options."""
    
    ALL = "all"
    PROFILES = "profiles"
    COMPANIES = "companies"
    POSTS = "posts"
    JOBS = "jobs"
    ARTICLES = "articles"


class SearchRequest(BaseModel):
    """Unified search request model for both single and multi-page searches."""
    
    query: str = Field(..., description="Search query string", min_length=1)
    country: str = Field(default="ID", description="Country code for search (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code for search (ISO 639-1)")
    
    # Single-page parameters (backward compatible)
    page: int = Field(default=1, description="Page number for single-page search", ge=1, le=100)
    results_per_page: int = Field(default=10, description="Results per page", ge=1, le=100)
    
    # Multi-page parameters (optional for batch functionality)
    max_pages: Optional[int] = Field(
        default=None, 
        description="Maximum pages to fetch for batch search. If specified, enables multi-page mode.", 
        ge=1, le=10
    )
    start_page: Optional[int] = Field(
        default=None, 
        description="Starting page number for batch search (defaults to 'page' value)", 
        ge=1
    )
    
    # Social platform filtering
    social_platform: SocialPlatform = Field(
        default=SocialPlatform.NONE, 
        description="Social media platform filter (none, instagram, linkedin)"
    )
    instagram_content_type: InstagramContentType = Field(
        default=InstagramContentType.ALL, 
        description="Instagram content type filter (all, reels, posts, accounts, tv, locations)"
    )
    linkedin_content_type: LinkedInContentType = Field(
        default=LinkedInContentType.ALL, 
        description="LinkedIn content type filter (all, profiles, companies, posts, jobs, articles)"
    )
    
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
    
    @field_validator('start_page')
    @classmethod
    def validate_start_page(cls, v: Optional[int], info) -> Optional[int]:
        """Validate start_page is compatible with max_pages."""
        if v is not None and info.data.get('max_pages') is None:
            raise ValueError('start_page can only be used with max_pages')
        return v
    
    def is_multi_page_request(self) -> bool:
        """Check if this is a multi-page request."""
        return self.max_pages is not None and self.max_pages > 1
    
    def get_effective_start_page(self) -> int:
        """Get the effective start page for batch processing."""
        return self.start_page if self.start_page is not None else self.page


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
    """Unified search response model for both single and multi-page results."""
    
    query: str = Field(..., description="Original search query")
    results_count: int = Field(..., description="Number of results returned", ge=0)
    organic_results: List[SearchResult] = Field(default=[], description="Organic search results")
    
    # Single-page response fields
    pagination: Optional[PaginationMetadata] = Field(None, description="Pagination metadata for single-page responses")
    
    # Multi-page response fields (only populated for multi-page requests)
    pages_fetched: Optional[int] = Field(None, description="Number of pages successfully fetched (multi-page only)")
    pages: Optional[List[PageResult]] = Field(None, description="Results for each fetched page (multi-page only)")
    merged_results: Optional[List[SearchResult]] = Field(None, description="All results merged with continuous ranking (multi-page only)")
    merged_metadata: Optional[MergedResultsMetadata] = Field(None, description="Metadata about merge operation (multi-page only)")
    pagination_summary: Optional[BatchPaginationSummary] = Field(None, description="Batch pagination summary (multi-page only)")
    
    # Common fields
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Response timestamp")
    search_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional search metadata")
    
    def is_multi_page_response(self) -> bool:
        """Check if this is a multi-page response."""
        return self.pages_fetched is not None and self.pages_fetched > 1
    
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


# BatchPaginationRequest has been merged into SearchRequest above
# Legacy alias for backward compatibility
BatchPaginationRequest = SearchRequest


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


class MergedResultsMetadata(BaseModel):
    """Metadata for merged pagination results."""
    
    total_merged_results: int = Field(..., description="Total number of results after merging", ge=0)
    continuous_rank_start: int = Field(..., description="First rank number in merged results", ge=1)
    continuous_rank_end: int = Field(..., description="Last rank number in merged results", ge=1)
    pages_included: List[int] = Field(..., description="Page numbers that were included in the merge")
    merge_processing_time: float = Field(..., description="Time taken to perform the merge operation in seconds")


class BatchPaginationResponse(BaseModel):
    """Response model for batch pagination searches."""
    
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total results across all fetched pages", ge=0)
    pages_fetched: int = Field(..., description="Number of pages successfully fetched", ge=0)
    pagination_summary: BatchPaginationSummary = Field(..., description="Batch pagination summary")
    pages: List[PageResult] = Field(default=[], description="Results for each fetched page")
    merged_results: List[SearchResult] = Field(default=[], description="All organic results merged with continuous ranking")
    merged_metadata: Optional[MergedResultsMetadata] = Field(None, description="Metadata about the merge operation")
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


