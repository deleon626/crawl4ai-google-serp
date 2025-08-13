"""Company data models for information extraction."""

from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, UTC
from enum import Enum
import re


class ExtractionMode(str, Enum):
    """Company information extraction modes."""
    
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    CONTACT_FOCUSED = "contact_focused"
    FINANCIAL_FOCUSED = "financial_focused"


class CompanySize(str, Enum):
    """Company size categories."""
    
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"


class CompanySector(str, Enum):
    """Common business sectors."""
    
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    EDUCATION = "education"
    CONSULTING = "consulting"
    REAL_ESTATE = "real_estate"
    MEDIA = "media"
    ENERGY = "energy"
    OTHER = "other"


class SocialPlatformType(str, Enum):
    """Social media platform types."""
    
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    GITHUB = "github"
    TIKTOK = "tiktok"
    CRUNCHBASE = "crunchbase"
    OTHER = "other"


class CompanyInformationRequest(BaseModel):
    """Request model for company information extraction."""
    
    # Primary search parameters
    company_name: str = Field(..., description="Company name to search for", min_length=1)
    domain: Optional[str] = Field(None, description="Company domain/website if known")
    
    # Search configuration
    extraction_mode: ExtractionMode = Field(
        default=ExtractionMode.COMPREHENSIVE,
        description="Level of information extraction (basic, comprehensive, contact_focused, financial_focused)"
    )
    country: str = Field(default="US", description="Country code for search (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code for search (ISO 639-1)")
    
    # Advanced search options
    include_subsidiaries: bool = Field(default=False, description="Include subsidiary companies in search")
    include_social_media: bool = Field(default=True, description="Extract social media information")
    include_financial_data: bool = Field(default=True, description="Extract financial information if available")
    include_contact_info: bool = Field(default=True, description="Extract contact information")
    include_key_personnel: bool = Field(default=False, description="Extract key personnel information")
    
    # Search constraints
    max_pages_to_crawl: int = Field(default=5, description="Maximum pages to crawl for information", ge=1, le=20)
    timeout_seconds: int = Field(default=30, description="Timeout for each crawl operation", ge=5, le=120)
    
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
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate domain format."""
        if v is None:
            return v
        
        # Remove protocol if present
        if v.startswith(('http://', 'https://')):
            v = v.split('://', 1)[1]
        
        # Remove trailing slash
        v = v.rstrip('/')
        
        # Basic domain validation
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
            r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )
        if not domain_pattern.match(v):
            raise ValueError('Invalid domain format')
        
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_name": "OpenAI",
                "domain": "openai.com",
                "extraction_mode": "comprehensive",
                "country": "US",
                "language": "en",
                "include_subsidiaries": False,
                "include_social_media": True,
                "include_financial_data": True,
                "include_contact_info": True,
                "include_key_personnel": False,
                "max_pages_to_crawl": 5,
                "timeout_seconds": 30
            }
        }
    )


class CompanyContact(BaseModel):
    """Company contact information model."""
    
    email: Optional[str] = Field(None, description="Primary company email")
    phone: Optional[str] = Field(None, description="Primary phone number")
    fax: Optional[str] = Field(None, description="Fax number")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    
    # Additional contact methods
    additional_emails: List[str] = Field(default=[], description="Additional email addresses")
    additional_phones: List[str] = Field(default=[], description="Additional phone numbers")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None:
            return v
        
        # Basic email validation pattern
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        if not email_pattern.match(v):
            raise ValueError('Invalid email format')
        
        return v
    
    @field_validator('phone', 'fax')
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone/fax number format."""
        if v is None:
            return v
        
        # Remove common separators for validation
        clean_number = re.sub(r'[^\d+]', '', v)
        if len(clean_number) < 7:  # Minimum reasonable phone number length
            raise ValueError('Phone number too short')
        
        return v
    
    @field_validator('additional_emails')
    @classmethod
    def validate_additional_emails(cls, v: List[str]) -> List[str]:
        """Validate additional email addresses."""
        validated = []
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        for email in v:
            if email_pattern.match(email):
                validated.append(email)
        return validated
    
    @field_validator('additional_phones')
    @classmethod
    def validate_additional_phones(cls, v: List[str]) -> List[str]:
        """Validate additional phone numbers."""
        validated = []
        for phone in v:
            clean_number = re.sub(r'[^\d+]', '', phone)
            if len(clean_number) >= 7:
                validated.append(phone)
        return validated
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "contact@openai.com",
                "phone": "+1-415-555-0123",
                "address": "3180 18th St, San Francisco, CA 94110",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "postal_code": "94110",
                "additional_emails": ["support@openai.com", "press@openai.com"],
                "additional_phones": ["+1-415-555-0124"]
            }
        }
    )


class CompanySocial(BaseModel):
    """Company social media information model."""
    
    platform: SocialPlatformType = Field(..., description="Social media platform type")
    url: HttpUrl = Field(..., description="URL to the company's profile")
    username: Optional[str] = Field(None, description="Username/handle on the platform")
    followers_count: Optional[int] = Field(None, description="Number of followers", ge=0)
    verified: Optional[bool] = Field(None, description="Whether the account is verified")
    
    @field_validator('url')
    @classmethod
    def validate_social_url(cls, v: HttpUrl, info) -> HttpUrl:
        """Validate social media URL matches platform."""
        url_str = str(v).lower()
        platform = info.data.get('platform')
        
        if not platform:
            return v
            
        platform_domains = {
            SocialPlatformType.LINKEDIN: ['linkedin.com'],
            SocialPlatformType.TWITTER: ['twitter.com', 'x.com'],
            SocialPlatformType.FACEBOOK: ['facebook.com'],
            SocialPlatformType.INSTAGRAM: ['instagram.com'],
            SocialPlatformType.YOUTUBE: ['youtube.com'],
            SocialPlatformType.GITHUB: ['github.com'],
            SocialPlatformType.TIKTOK: ['tiktok.com'],
            SocialPlatformType.CRUNCHBASE: ['crunchbase.com']
        }
        
        expected_domains = platform_domains.get(platform, [])
        if expected_domains and not any(domain in url_str for domain in expected_domains):
            raise ValueError(f'URL does not match platform {platform}')
        
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "linkedin",
                "url": "https://linkedin.com/company/openai",
                "username": "openai",
                "followers_count": 250000,
                "verified": True
            }
        }
    )


class CompanyBasicInfo(BaseModel):
    """Basic company information model."""
    
    # Core identification
    name: str = Field(..., description="Official company name", min_length=1)
    legal_name: Optional[str] = Field(None, description="Legal company name")
    domain: Optional[str] = Field(None, description="Primary company domain")
    website: Optional[HttpUrl] = Field(None, description="Primary company website")
    
    # Business details
    description: Optional[str] = Field(None, description="Company description")
    tagline: Optional[str] = Field(None, description="Company tagline or slogan")
    industry: Optional[str] = Field(None, description="Primary industry")
    sector: Optional[CompanySector] = Field(None, description="Business sector category")
    founded_year: Optional[int] = Field(None, description="Year company was founded", ge=1800, le=2030)
    
    # Size and scale
    company_size: Optional[CompanySize] = Field(None, description="Company size category")
    employee_count: Optional[int] = Field(None, description="Approximate number of employees", ge=0)
    employee_count_range: Optional[str] = Field(None, description="Employee count range (e.g., '51-200')")
    
    # Location
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    locations: List[str] = Field(default=[], description="Additional office locations")
    
    # Identifiers
    stock_symbol: Optional[str] = Field(None, description="Stock ticker symbol")
    is_public: Optional[bool] = Field(None, description="Whether company is publicly traded")
    
    @field_validator('founded_year')
    @classmethod
    def validate_founded_year(cls, v: Optional[int]) -> Optional[int]:
        """Validate founded year is reasonable."""
        if v is None:
            return v
        
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError('Founded year cannot be in the future')
        
        return v
    
    @field_validator('stock_symbol')
    @classmethod
    def validate_stock_symbol(cls, v: Optional[str]) -> Optional[str]:
        """Validate stock symbol format."""
        if v is None:
            return v
        
        # Basic stock symbol validation (letters, numbers, some special chars)
        if not re.match(r'^[A-Z0-9.-]{1,10}$', v.upper()):
            raise ValueError('Invalid stock symbol format')
        
        return v.upper()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "OpenAI",
                "legal_name": "OpenAI, L.L.C.",
                "domain": "openai.com",
                "website": "https://openai.com",
                "description": "AI research and deployment company",
                "tagline": "Creating safe AGI that benefits all of humanity",
                "industry": "Artificial Intelligence",
                "sector": "technology",
                "founded_year": 2015,
                "company_size": "medium",
                "employee_count": 500,
                "employee_count_range": "201-500",
                "headquarters": "San Francisco, CA, USA",
                "locations": ["San Francisco, CA", "London, UK"],
                "is_public": False
            }
        }
    )


class CompanyFinancials(BaseModel):
    """Company financial information model."""
    
    revenue: Optional[str] = Field(None, description="Annual revenue")
    revenue_currency: Optional[str] = Field(None, description="Revenue currency code")
    funding_total: Optional[str] = Field(None, description="Total funding raised")
    funding_currency: Optional[str] = Field(None, description="Funding currency code")
    last_funding_round: Optional[str] = Field(None, description="Last funding round type")
    last_funding_date: Optional[str] = Field(None, description="Last funding date")
    valuation: Optional[str] = Field(None, description="Company valuation")
    valuation_currency: Optional[str] = Field(None, description="Valuation currency code")
    investors: List[str] = Field(default=[], description="List of investors")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "revenue": "100M+",
                "revenue_currency": "USD",
                "funding_total": "11.3B",
                "funding_currency": "USD",
                "last_funding_round": "Series C",
                "last_funding_date": "2023-04-28",
                "valuation": "29B",
                "valuation_currency": "USD",
                "investors": ["Microsoft", "Andreessen Horowitz", "Sequoia Capital"]
            }
        }
    )


class CompanyKeyPersonnel(BaseModel):
    """Company key personnel model."""
    
    name: str = Field(..., description="Person's name", min_length=1)
    title: str = Field(..., description="Job title/position", min_length=1)
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    email: Optional[str] = Field(None, description="Email address")
    bio: Optional[str] = Field(None, description="Brief biography")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None:
            return v
        
        # Basic email validation pattern
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        if not email_pattern.match(v):
            raise ValueError('Invalid email format')
        
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sam Altman",
                "title": "CEO",
                "linkedin_url": "https://linkedin.com/in/sam-altman",
                "bio": "CEO of OpenAI, former president of Y Combinator"
            }
        }
    )


class CompanyInformation(BaseModel):
    """Aggregated company information model."""
    
    basic_info: CompanyBasicInfo = Field(..., description="Basic company information")
    contact: Optional[CompanyContact] = Field(None, description="Company contact information")
    social_media: List[CompanySocial] = Field(default=[], description="Social media profiles")
    financials: Optional[CompanyFinancials] = Field(None, description="Financial information")
    key_personnel: List[CompanyKeyPersonnel] = Field(default=[], description="Key personnel")
    
    # Metadata
    data_quality_score: Optional[float] = Field(
        None, 
        description="Data quality score (0-1)", 
        ge=0.0, 
        le=1.0
    )
    completeness_score: Optional[float] = Field(
        None, 
        description="Information completeness score (0-1)", 
        ge=0.0, 
        le=1.0
    )
    confidence_score: Optional[float] = Field(
        None, 
        description="Overall confidence in extracted data (0-1)", 
        ge=0.0, 
        le=1.0
    )
    
    def get_primary_email(self) -> Optional[str]:
        """Get the primary company email."""
        return str(self.contact.email) if self.contact and self.contact.email else None
    
    def get_primary_phone(self) -> Optional[str]:
        """Get the primary company phone."""
        return self.contact.phone if self.contact else None
    
    def get_social_by_platform(self, platform: SocialPlatformType) -> Optional[CompanySocial]:
        """Get social media profile by platform."""
        for social in self.social_media:
            if social.platform == platform:
                return social
        return None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "basic_info": {
                    "name": "OpenAI",
                    "legal_name": "OpenAI, L.L.C.",
                    "domain": "openai.com",
                    "website": "https://openai.com",
                    "description": "AI research and deployment company",
                    "industry": "Artificial Intelligence",
                    "sector": "technology",
                    "founded_year": 2015,
                    "company_size": "medium",
                    "employee_count": 500,
                    "headquarters": "San Francisco, CA, USA"
                },
                "contact": {
                    "email": "contact@openai.com",
                    "address": "3180 18th St, San Francisco, CA 94110",
                    "city": "San Francisco",
                    "state": "CA",
                    "country": "United States"
                },
                "social_media": [
                    {
                        "platform": "linkedin",
                        "url": "https://linkedin.com/company/openai",
                        "followers_count": 250000,
                        "verified": True
                    }
                ],
                "data_quality_score": 0.85,
                "completeness_score": 0.75,
                "confidence_score": 0.90
            }
        }
    )


class ExtractionError(BaseModel):
    """Error information for failed extractions."""
    
    error_type: str = Field(..., description="Type of error encountered")
    error_message: str = Field(..., description="Detailed error message")
    url: Optional[str] = Field(None, description="URL where error occurred")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_type": "TimeoutError",
                "error_message": "Request timed out after 30 seconds",
                "url": "https://example.com/about",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    )


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""
    
    pages_crawled: int = Field(..., description="Number of pages successfully crawled", ge=0)
    pages_attempted: int = Field(..., description="Number of pages attempted to crawl", ge=0)
    extraction_time: float = Field(..., description="Total extraction time in seconds", ge=0)
    sources_found: List[str] = Field(default=[], description="URLs where information was found")
    search_queries_used: List[str] = Field(default=[], description="Search queries used for discovery")
    extraction_mode_used: ExtractionMode = Field(..., description="Extraction mode used")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pages_crawled": 5,
                "pages_attempted": 7,
                "extraction_time": 45.2,
                "sources_found": [
                    "https://openai.com/about",
                    "https://openai.com/contact",
                    "https://linkedin.com/company/openai"
                ],
                "search_queries_used": [
                    "OpenAI company information",
                    "OpenAI contact details",
                    "OpenAI headquarters address"
                ],
                "extraction_mode_used": "comprehensive"
            }
        }
    )


class CompanyExtractionResponse(BaseModel):
    """Response model for company information extraction."""
    
    request_id: str = Field(..., description="Unique request identifier")
    company_name: str = Field(..., description="Original company name searched")
    
    # Results
    success: bool = Field(..., description="Whether extraction was successful")
    company_information: Optional[CompanyInformation] = Field(
        None, 
        description="Extracted company information (null if extraction failed)"
    )
    
    # Metadata and diagnostics
    extraction_metadata: ExtractionMetadata = Field(..., description="Extraction process metadata")
    errors: List[ExtractionError] = Field(default=[], description="Errors encountered during extraction")
    warnings: List[str] = Field(default=[], description="Non-fatal warnings")
    
    # Response metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Response timestamp")
    processing_time: float = Field(..., description="Total processing time in seconds", ge=0)
    
    def has_errors(self) -> bool:
        """Check if extraction had any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if extraction had any warnings."""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.errors:
            return "No errors"
        
        error_types = [error.error_type for error in self.errors]
        return f"{len(self.errors)} errors: {', '.join(set(error_types))}"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_123456789",
                "company_name": "OpenAI",
                "success": True,
                "company_information": {
                    "basic_info": {
                        "name": "OpenAI",
                        "domain": "openai.com",
                        "website": "https://openai.com",
                        "description": "AI research and deployment company",
                        "industry": "Artificial Intelligence",
                        "founded_year": 2015,
                        "headquarters": "San Francisco, CA, USA"
                    },
                    "contact": {
                        "email": "contact@openai.com",
                        "address": "3180 18th St, San Francisco, CA 94110"
                    },
                    "data_quality_score": 0.85
                },
                "extraction_metadata": {
                    "pages_crawled": 5,
                    "pages_attempted": 5,
                    "extraction_time": 45.2,
                    "sources_found": ["https://openai.com/about"],
                    "extraction_mode_used": "comprehensive"
                },
                "errors": [],
                "warnings": [],
                "processing_time": 47.5
            }
        }
    )