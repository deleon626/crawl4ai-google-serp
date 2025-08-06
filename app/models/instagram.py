"""Instagram analysis data models."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


class InstagramSearchRequest(BaseModel):
    """Instagram business search request model."""
    
    business_type: Optional[str] = Field(None, description="Type of business to search for")
    location: Optional[str] = Field(None, description="Geographic location filter")
    keywords: Optional[List[str]] = Field(None, description="Additional search keywords")
    include_contact_info: bool = Field(True, description="Include contact information indicators")
    max_results: int = Field(10, description="Maximum number of results to return", ge=1, le=50)


class InstagramAnalysisRequest(BaseModel):
    """Instagram profile analysis request model."""
    
    url: HttpUrl = Field(..., description="Instagram profile URL to analyze")
    crawl_content: bool = Field(True, description="Whether to crawl profile content")
    analyze_bio: bool = Field(True, description="Whether to analyze bio for business indicators")
    extract_links: bool = Field(True, description="Whether to extract and validate links")
    extract_keywords: bool = Field(True, description="Whether to extract keywords")
    validate_links: bool = Field(False, description="Whether to validate link accessibility")


class BusinessIndicators(BaseModel):
    """Business indicators extracted from profile."""
    
    contact_info: List[str] = Field(default_factory=list, description="Types of contact info found")
    business_signals: List[str] = Field(default_factory=list, description="Business signal indicators")
    professional_markers: List[str] = Field(default_factory=list, description="Professional markers")
    location_info: List[str] = Field(default_factory=list, description="Location information")


class ExtractedData(BaseModel):
    """Data extracted from profile."""
    
    emails: List[str] = Field(default_factory=list, description="Email addresses found")
    phones: List[str] = Field(default_factory=list, description="Phone numbers found")
    websites: List[str] = Field(default_factory=list, description="Website URLs found")
    social_handles: List[str] = Field(default_factory=list, description="Social media handles found")


class BusinessAnalysis(BaseModel):
    """Business analysis results."""
    
    is_business: bool = Field(..., description="Whether profile appears to be business-related")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    indicators: BusinessIndicators = Field(..., description="Business indicators found")
    extracted_data: ExtractedData = Field(..., description="Extracted contact data")


class LinkInfo(BaseModel):
    """Information about an extracted link."""
    
    url: str = Field(..., description="The extracted URL")
    original_text: str = Field(..., description="Original text containing the link")
    link_type: str = Field(..., description="Type of link (website, social, email, phone, etc.)")
    domain: str = Field(..., description="Domain of the link")
    is_business_link: bool = Field(..., description="Whether link appears business-relevant")
    confidence: float = Field(..., description="Business relevance confidence score")
    validation_status: Optional[str] = Field(None, description="Link validation status")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    status_code: Optional[int] = Field(None, description="HTTP status code")


class LinkAnalysis(BaseModel):
    """Link extraction and validation results."""
    
    total_links: int = Field(..., description="Total number of links found")
    business_links: List[LinkInfo] = Field(default_factory=list, description="Business-relevant links")
    social_links: List[LinkInfo] = Field(default_factory=list, description="Social media links")
    contact_links: List[LinkInfo] = Field(default_factory=list, description="Contact links (email/phone)")
    website_links: List[LinkInfo] = Field(default_factory=list, description="Website links")
    summary: Dict[str, int] = Field(default_factory=dict, description="Link count summary")


class KeywordInfo(BaseModel):
    """Information about an extracted keyword."""
    
    keyword: str = Field(..., description="The extracted keyword or phrase")
    frequency: int = Field(..., description="Frequency of occurrence")
    relevance_score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    category: str = Field(..., description="Keyword category")
    variations: List[str] = Field(default_factory=list, description="Keyword variations found")
    context_examples: List[str] = Field(default_factory=list, description="Context examples")


class KeywordAnalysis(BaseModel):
    """Keyword extraction results."""
    
    keywords: List[KeywordInfo] = Field(default_factory=list, description="Extracted keywords")
    groups: Dict[str, List[KeywordInfo]] = Field(default_factory=dict, description="Grouped keywords")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Keyword analysis summary")
    top_business_keywords: List[KeywordInfo] = Field(default_factory=list, description="Top business keywords")


class InstagramAnalysisResult(BaseModel):
    """Instagram profile analysis result."""
    
    profile_url: HttpUrl = Field(..., description="Analyzed profile URL")
    profile_title: Optional[str] = Field(None, description="Profile title/name")
    business_analysis: BusinessAnalysis = Field(..., description="Business analysis results")
    business_category: Optional[str] = Field(None, description="Detected business category")
    link_analysis: Optional[LinkAnalysis] = Field(None, description="Link extraction results")
    keyword_analysis: Optional[KeywordAnalysis] = Field(None, description="Keyword extraction results")
    crawl_success: bool = Field(..., description="Whether content crawling succeeded")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InstagramAnalysisResponse(BaseModel):
    """Instagram analysis API response."""
    
    success: bool = Field(..., description="Whether analysis was successful")
    result: Optional[InstagramAnalysisResult] = Field(None, description="Analysis result")
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    execution_time: float = Field(..., description="Time taken for analysis in seconds")
    queries_generated: Optional[List[str]] = Field(None, description="Search queries generated for business search")


class InstagramSearchResponse(BaseModel):
    """Instagram search API response."""
    
    success: bool = Field(..., description="Whether search was successful")
    queries: List[str] = Field(..., description="Generated search queries")
    search_results: Optional[List[Dict[str, Any]]] = Field(None, description="Search results from SERP")
    analyzed_profiles: Optional[List[InstagramAnalysisResult]] = Field(None, description="Analyzed Instagram profiles")
    total_results: int = Field(default=0, description="Total number of results")
    execution_time: float = Field(..., description="Time taken for search in seconds")
    error: Optional[str] = Field(None, description="Error message if search failed")