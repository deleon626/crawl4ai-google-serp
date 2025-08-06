"""Crawl4ai data models."""

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CrawlRequest(BaseModel):
    """Crawl request model."""
    
    url: HttpUrl = Field(..., description="URL to crawl")
    include_raw_html: Optional[bool] = Field(default=False, description="Include raw HTML in response")
    word_count_threshold: Optional[int] = Field(default=10, description="Minimum word count threshold")
    extraction_strategy: Optional[str] = Field(default="NoExtractionStrategy", description="Content extraction strategy")
    chunking_strategy: Optional[str] = Field(default="RegexChunking", description="Content chunking strategy")
    css_selector: Optional[str] = Field(None, description="CSS selector for content extraction")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")


class CrawlResult(BaseModel):
    """Crawl result model."""
    
    url: HttpUrl = Field(..., description="Crawled URL")
    title: Optional[str] = Field(None, description="Page title")
    markdown: Optional[str] = Field(None, description="Page content in markdown format")
    cleaned_html: Optional[str] = Field(None, description="Cleaned HTML content")
    media: Optional[Dict[str, List[str]]] = Field(None, description="Extracted media (images, videos, etc.)")
    links: Optional[Dict[str, List[str]]] = Field(None, description="Extracted links")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Page metadata")


class CrawlResponse(BaseModel):
    """Crawl API response model."""
    
    success: bool = Field(..., description="Whether the crawl was successful")
    url: HttpUrl = Field(..., description="Original URL")
    result: Optional[CrawlResult] = Field(None, description="Crawl result data")
    error: Optional[str] = Field(None, description="Error message if crawl failed")
    execution_time: float = Field(..., description="Time taken for crawl in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")