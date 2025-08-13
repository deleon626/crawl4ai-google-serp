# Company Information Extraction Feature - Design Specification

## Feature Overview

The **Company Information Extraction** feature enhances the existing crawl4ai integration to systematically extract structured company information from corporate websites. This builds upon the current Phase 2 crawl4ai infrastructure while adding specialized parsing capabilities for business intelligence gathering.

## Architecture Design

### 1. System Architecture

The feature follows the existing service-oriented architecture pattern:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SERP Search   │────│  URL Discovery  │────│ Company Extract │
│   (Existing)    │    │   (Enhanced)    │    │     (NEW)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐              ┌────▼────┐              ┌────▼────┐
    │ Bright  │              │ Crawl4ai│              │ Company │
    │ Data    │              │ Client  │              │ Info    │
    │ Client  │              │ (Exists)│              │ Parser  │
    │(Exists) │              │         │              │  (NEW)  │
    └─────────┘              └─────────┘              └─────────┘
```

### 2. Component Design

#### A. Enhanced Data Models (`app/models/company.py`)
```python
class CompanyInformationRequest(BaseModel):
    """Company information extraction request."""
    
    # Search parameters
    company_name: str = Field(..., description="Company name to search for")
    company_domain: Optional[str] = Field(None, description="Known company domain")
    search_country: str = Field("US", description="Search country code")
    search_language: str = Field("en", description="Search language code")
    
    # Extraction configuration
    extraction_scope: List[str] = Field(
        default=["basic", "contact", "social"], 
        description="Types of information to extract"
    )
    max_pages_to_crawl: int = Field(default=5, description="Maximum pages to crawl per company")
    include_subsidiaries: bool = Field(default=False, description="Include subsidiary information")
    
    # Advanced options
    custom_css_selectors: Optional[Dict[str, str]] = Field(None, description="Custom CSS selectors")
    crawl_timeout: int = Field(default=30, description="Crawl timeout per page in seconds")

class CompanyContact(BaseModel):
    """Company contact information."""
    
    emails: List[str] = Field(default_factory=list, description="Email addresses")
    phone_numbers: List[str] = Field(default_factory=list, description="Phone numbers")
    addresses: List[str] = Field(default_factory=list, description="Physical addresses")
    fax_numbers: List[str] = Field(default_factory=list, description="Fax numbers")

class CompanySocial(BaseModel):
    """Company social media presence."""
    
    linkedin: Optional[str] = Field(None, description="LinkedIn company URL")
    twitter: Optional[str] = Field(None, description="Twitter/X company URL")
    facebook: Optional[str] = Field(None, description="Facebook company URL")
    instagram: Optional[str] = Field(None, description="Instagram company URL")
    youtube: Optional[str] = Field(None, description="YouTube company URL")
    github: Optional[str] = Field(None, description="GitHub organization URL")

class CompanyBasicInfo(BaseModel):
    """Basic company information."""
    
    company_name: str = Field(..., description="Official company name")
    industry: Optional[str] = Field(None, description="Company industry")
    founded_year: Optional[int] = Field(None, description="Year company was founded")
    employee_count: Optional[str] = Field(None, description="Employee count range")
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, description="Official website URL")
    logo_url: Optional[str] = Field(None, description="Company logo URL")

class CompanyInformation(BaseModel):
    """Complete company information structure."""
    
    basic_info: CompanyBasicInfo = Field(..., description="Basic company information")
    contact: CompanyContact = Field(default_factory=CompanyContact, description="Contact information")
    social: CompanySocial = Field(default_factory=CompanySocial, description="Social media presence")
    additional_data: Dict[str, Any] = Field(default_factory=dict, description="Additional extracted data")

class CompanyExtractionResponse(BaseModel):
    """Company information extraction response."""
    
    success: bool = Field(..., description="Whether extraction was successful")
    company_name: str = Field(..., description="Searched company name")
    company_info: Optional[CompanyInformation] = Field(None, description="Extracted company information")
    pages_crawled: List[str] = Field(default_factory=list, description="URLs crawled")
    extraction_errors: List[str] = Field(default_factory=list, description="Extraction errors")
    execution_time: float = Field(..., description="Total execution time")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
```

#### B. Company Information Parser (`app/parsers/company_parser.py`)
```python
class CompanyInformationParser:
    """Parser for extracting structured company information from web content."""
    
    # Extraction patterns for different information types
    EMAIL_PATTERNS = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ]
    
    PHONE_PATTERNS = [
        r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
        r'\+?[0-9]{1,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}'
    ]
    
    SOCIAL_PATTERNS = {
        'linkedin': r'https?://(?:www\.)?linkedin\.com/company/[^/\s]+',
        'twitter': r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^/\s]+',
        'facebook': r'https?://(?:www\.)?facebook\.com/[^/\s]+',
        'instagram': r'https?://(?:www\.)?instagram\.com/[^/\s]+',
        'youtube': r'https?://(?:www\.)?youtube\.com/(?:channel|user|c)/[^/\s]+',
        'github': r'https?://(?:www\.)?github\.com/[^/\s]+'
    }
    
    # CSS selectors for common company information locations
    COMPANY_SELECTORS = {
        'about_pages': ['a[href*="about"]', 'a[href*="company"]', 'a[href*="who-we-are"]'],
        'contact_pages': ['a[href*="contact"]', 'a[href*="reach-us"]', 'a[href*="get-in-touch"]'],
        'footer_info': ['footer', '.footer', '#footer', '.site-footer'],
        'header_info': ['header', '.header', '#header', '.site-header'],
        'meta_description': ['meta[name="description"]', 'meta[property="og:description"]'],
        'company_name': ['h1', '.company-name', '.brand-name', '.logo-text'],
    }
    
    def extract_company_information(
        self, 
        html_content: str, 
        url: str, 
        extraction_scope: List[str]
    ) -> Dict[str, Any]:
        """Extract company information from HTML content."""
        
    def _extract_basic_info(self, soup: BeautifulSoup, url: str) -> CompanyBasicInfo:
        """Extract basic company information."""
        
    def _extract_contact_info(self, soup: BeautifulSoup) -> CompanyContact:
        """Extract contact information."""
        
    def _extract_social_media(self, soup: BeautifulSoup) -> CompanySocial:
        """Extract social media information."""
        
    def _extract_from_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract information from JSON-LD structured data."""
```

#### C. Company Extraction Service (`app/services/company_service.py`)
```python
class CompanyExtractionService:
    """Service for extracting company information through search and crawl operations."""
    
    def __init__(self):
        self.serp_service = None  # Will initialize in context manager
        self.crawl_service = None  # Will initialize in context manager
        self.company_parser = CompanyInformationParser()
    
    async def extract_company_information(
        self, 
        request: CompanyInformationRequest
    ) -> CompanyExtractionResponse:
        """Main method to extract company information."""
        
        # Phase 1: Discover company URLs via SERP search
        company_urls = await self._discover_company_urls(request)
        
        # Phase 2: Crawl discovered URLs
        crawl_results = await self._crawl_company_pages(company_urls, request)
        
        # Phase 3: Parse and extract structured information
        company_info = await self._parse_company_information(crawl_results, request)
        
        return company_info
    
    async def _discover_company_urls(self, request: CompanyInformationRequest) -> List[str]:
        """Discover company URLs using SERP search."""
        
    async def _crawl_company_pages(self, urls: List[str], request: CompanyInformationRequest) -> List[Dict]:
        """Crawl company pages and extract content."""
        
    async def _parse_company_information(self, crawl_results: List[Dict], request: CompanyInformationRequest) -> CompanyExtractionResponse:
        """Parse crawled content and extract structured company information."""
```

### 3. API Endpoints

#### New Router: `app/routers/company.py`
```python
@router.post("/company/extract", response_model=CompanyExtractionResponse)
async def extract_company_information(request: CompanyInformationRequest):
    """Extract comprehensive company information from web sources."""

@router.post("/company/search-and-extract", response_model=CompanyExtractionResponse) 
async def search_and_extract_company(request: CompanyInformationRequest):
    """Search for company and extract information in one operation."""

@router.get("/company/extraction-scopes")
async def get_extraction_scopes():
    """Get available extraction scope options."""
    return {
        "scopes": ["basic", "contact", "social", "financial", "news", "jobs"],
        "descriptions": {
            "basic": "Company name, industry, description, headquarters",
            "contact": "Email addresses, phone numbers, physical addresses",
            "social": "Social media profiles and URLs",
            "financial": "Revenue, funding information (if publicly available)",
            "news": "Recent company news and press releases",
            "jobs": "Current job openings and career information"
        }
    }
```

### 4. Extraction Patterns & Logic Specification

#### A. Information Discovery Strategy
```python
# Multi-stage URL discovery approach:
COMPANY_SEARCH_QUERIES = [
    "{company_name} official website",
    "{company_name} company information", 
    "{company_name} contact information",
    "{company_name} about us",
    "site:{company_domain}" if domain_known else None
]

# Priority scoring for discovered URLs:
URL_PRIORITY_PATTERNS = {
    'official_site': {'score': 100, 'patterns': [domain_match]},
    'about_page': {'score': 90, 'patterns': ['/about', '/company', '/who-we-are']},
    'contact_page': {'score': 85, 'patterns': ['/contact', '/reach-us']},
    'careers_page': {'score': 70, 'patterns': ['/careers', '/jobs']},
    'news_page': {'score': 65, 'patterns': ['/news', '/press']},
    'social_profiles': {'score': 60, 'patterns': ['linkedin.com', 'twitter.com']}
}
```

#### B. Content Extraction Rules
```python
EXTRACTION_RULES = {
    'basic_info': {
        'company_name': {
            'selectors': ['h1', '.company-name', '.brand', 'title'],
            'patterns': [r'^([^|]+)', r'^([^-]+)'],  # Extract before separators
            'validation': lambda x: len(x) > 2 and len(x) < 100
        },
        'industry': {
            'selectors': ['.industry', '.business-type', '[itemprop="industry"]'],
            'keywords': ['industry', 'sector', 'business type', 'field'],
            'ml_extraction': True  # Use LLM extraction as fallback
        },
        'description': {
            'selectors': ['meta[name="description"]', '.company-description', '.about-text'],
            'max_length': 500,
            'clean_html': True
        }
    },
    
    'contact_info': {
        'email_extraction': {
            'patterns': EMAIL_PATTERNS,
            'exclude_patterns': [r'noreply@', r'example@', r'test@'],
            'domain_validation': True
        },
        'phone_extraction': {
            'patterns': PHONE_PATTERNS,
            'context_keywords': ['phone', 'call', 'telephone', 'contact'],
            'format_standardization': True
        },
        'address_extraction': {
            'selectors': ['.address', '.location', '[itemprop="address"]'],
            'patterns': [ADDRESS_PATTERNS],
            'geocoding_validation': False  # Optional enhancement
        }
    },
    
    'social_media': {
        'link_extraction': SOCIAL_PATTERNS,
        'verification': {
            'check_active': False,  # Optional enhancement
            'extract_follower_count': False  # Optional enhancement
        }
    }
}
```

#### C. Quality Validation & Confidence Scoring
```python
QUALITY_VALIDATION = {
    'confidence_scoring': {
        'high_confidence': {
            'threshold': 0.8,
            'criteria': [
                'official_domain_match',
                'multiple_source_confirmation',
                'structured_data_present'
            ]
        },
        'medium_confidence': {
            'threshold': 0.6,
            'criteria': [
                'single_source_confirmation',
                'pattern_match_success'
            ]
        },
        'low_confidence': {
            'threshold': 0.3,
            'criteria': [
                'weak_pattern_match',
                'no_structured_data'
            ]
        }
    },
    
    'validation_rules': {
        'email_validation': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone_validation': 'standardize_format',
        'url_validation': 'check_accessibility',
        'duplicate_detection': 'fuzzy_matching'
    }
}
```

### 5. Integration Points

#### A. Enhanced Search Strategy
- **Phase 1**: Use existing SERP search to discover company URLs
- **Phase 2**: Rank URLs by relevance and information potential
- **Phase 3**: Selective crawling based on priority scoring

#### B. Crawl4ai Enhancement
- Leverage existing `Crawl4aiClient` with specialized configurations
- Add company-specific extraction strategies
- Implement parallel crawling for multiple pages

#### C. Error Handling & Resilience
```python
ERROR_HANDLING_STRATEGY = {
    'rate_limiting': {
        'respect_robots_txt': True,
        'crawl_delay': 1,  # seconds between requests
        'max_concurrent': 3
    },
    
    'failure_recovery': {
        'retry_failed_urls': True,
        'max_retries': 2,
        'fallback_strategies': [
            'try_alternative_selectors',
            'use_llm_extraction',
            'return_partial_results'
        ]
    },
    
    'data_validation': {
        'sanitize_extracted_data': True,
        'remove_duplicates': True,
        'confidence_thresholds': True
    }
}
```

### 6. Performance Considerations

#### A. Caching Strategy
- Cache SERP results for company searches (1 hour TTL)
- Cache successful company extractions (24 hour TTL)
- Implement Redis integration for production scaling

#### B. Resource Management
- Limit concurrent crawling operations
- Implement timeout controls for long-running extractions
- Monitor memory usage for large-scale operations

#### C. Scalability Design
- Support for batch company processing
- Queue-based processing for large requests
- Configurable extraction depth and scope

## Implementation Roadmap

### Phase 3A: Foundation (Week 1-2)
1. **Create Data Models** - Implement `CompanyInformationRequest`, `CompanyInformation`, and `CompanyExtractionResponse` models
2. **Basic Parser** - Develop `CompanyInformationParser` with core extraction patterns
3. **Service Layer** - Build `CompanyExtractionService` with search integration

### Phase 3B: Core Features (Week 3-4)
1. **API Endpoints** - Implement company extraction endpoints
2. **Integration Testing** - Test with real company websites
3. **Error Handling** - Add comprehensive error handling and validation

### Phase 3C: Enhancement (Week 5-6)
1. **Advanced Patterns** - Add machine learning-based extraction
2. **Batch Processing** - Support for multiple company extraction
3. **Performance Optimization** - Caching and concurrent processing

### Phase 3D: Production Readiness (Week 7-8)
1. **Security & Compliance** - Rate limiting and robots.txt compliance
2. **Monitoring & Logging** - Enhanced observability
3. **Documentation & Testing** - Complete test coverage and API docs

## Technical Benefits

1. **Leverages Existing Infrastructure** - Builds on proven SERP + Crawl4ai foundation
2. **Modular Design** - Each component can be developed and tested independently
3. **Scalable Architecture** - Supports both single company and batch processing
4. **Flexible Extraction** - Configurable extraction scopes and custom selectors
5. **Production-Ready** - Includes error handling, validation, and monitoring

## Business Value

1. **Automated Business Intelligence** - Extract company information at scale
2. **Lead Generation Enhancement** - Enrich prospect data with comprehensive company profiles
3. **Market Research Automation** - Analyze competitor information systematically
4. **Integration Ready** - API-first design for easy integration with existing tools

## Success Metrics

### Technical Metrics
- 90%+ extraction accuracy for basic company information
- <30 second average extraction time per company
- 95%+ API uptime and reliability
- Support for 100+ concurrent extractions

### Quality Metrics
- 90%+ code coverage with unit tests
- Zero critical security vulnerabilities
- <5% false positive rate in extracted data
- Support for top 50 website architectures

### Business Metrics
- Extract information from 95%+ of Fortune 500 company websites
- Support 10+ extraction scopes with configurable depth
- Enable batch processing of 1000+ companies per operation
- Provide structured data export in multiple formats

This design provides a comprehensive, production-ready approach to company information extraction that seamlessly integrates with the existing crawl4ai Google SERP infrastructure while adding significant new capabilities for business intelligence and data enrichment use cases.