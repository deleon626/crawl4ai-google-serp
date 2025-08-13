"""Shared test configuration and fixtures for company extraction tests."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

# Import resilience utilities first to ensure decorators are available
from app.utils.resilience import resilient_operation

# Now we can safely import the company service
from app.services.company_service import CompanyExtractionService
from app.parsers.company_parser import CompanyInformationParser
from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, CompanyInformation,
    CompanyBasicInfo, CompanyContact, CompanySocial, CompanyFinancials,
    CompanyKeyPersonnel, ExtractionMetadata, ExtractionError, ExtractionMode,
    SocialPlatformType, CompanySize, CompanySector
)
from app.models.serp import SearchResponse, SearchResult
from app.models.crawl import CrawlResponse, CrawlResult

# Import fixtures from the fixtures module
from tests.fixtures.company_fixtures import *


# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def sample_html_files(test_data_dir):
    """Dictionary of sample HTML files for testing."""
    html_files = {}
    
    # Load all HTML files in test data directory
    for html_file in test_data_dir.glob("*.html"):
        with open(html_file, 'r', encoding='utf-8') as f:
            html_files[html_file.stem] = f.read()
    
    return html_files


@pytest.fixture
async def mock_company_service():
    """Create a mocked company extraction service."""
    service = CompanyExtractionService()
    
    # Mock the service dependencies
    service.serp_service = AsyncMock()
    service.crawl_service = AsyncMock()
    service.company_parser = MagicMock(spec=CompanyInformationParser)
    
    return service


@pytest.fixture
def company_parser():
    """Create a company information parser instance."""
    return CompanyInformationParser()


@pytest.fixture
def mock_successful_search_response():
    """Mock successful SERP search response."""
    return SearchResponse(
        query="TestCorp company information",
        results_count=5,
        organic_results=[
            SearchResult(
                rank=1,
                title="TestCorp - Home",
                url="https://testcorp.com",
                description="TestCorp official website"
            ),
            SearchResult(
                rank=2,
                title="TestCorp - About Us",
                url="https://testcorp.com/about",
                description="Learn about TestCorp's mission and team"
            ),
            SearchResult(
                rank=3,
                title="TestCorp - Contact",
                url="https://testcorp.com/contact", 
                description="Get in touch with TestCorp"
            ),
            SearchResult(
                rank=4,
                title="TestCorp | LinkedIn",
                url="https://linkedin.com/company/testcorp",
                description="TestCorp company page on LinkedIn"
            ),
            SearchResult(
                rank=5,
                title="TestCorp on Twitter",
                url="https://twitter.com/testcorp",
                description="Follow TestCorp for updates"
            )
        ],
        search_metadata={"total_results": 50000, "time_taken": 0.5}
    )


@pytest.fixture
def mock_successful_crawl_response():
    """Mock successful crawl response."""
    return CrawlResponse(
        success=True,
        url="https://testcorp.com/about",
        result=CrawlResult(
            url="https://testcorp.com/about",
            title="TestCorp - About Us",
            markdown="""# TestCorp

TestCorp is a leading technology company founded in 2015, specializing in innovative software solutions.

## Company Information
- **Founded**: 2015
- **Employees**: 150+ team members  
- **Headquarters**: San Francisco, California
- **Industry**: Technology & Software Development

## Leadership Team
- John Smith, CEO - Leading strategic vision
- Sarah Johnson, CTO - Technical innovation
- Michael Brown, CFO - Financial operations

## Contact
- Email: contact@testcorp.com
- Phone: +1-555-123-4567
- Address: 123 Innovation Drive, San Francisco, CA 94105
""",
            cleaned_html="""<h1>TestCorp</h1>
<p>TestCorp is a leading technology company founded in 2015, specializing in innovative software solutions.</p>
<h2>Company Information</h2>
<ul>
<li><strong>Founded</strong>: 2015</li>
<li><strong>Employees</strong>: 150+ team members</li>
<li><strong>Headquarters</strong>: San Francisco, California</li>
<li><strong>Industry</strong>: Technology &amp; Software Development</li>
</ul>
<h2>Leadership Team</h2>
<ul>
<li>John Smith, CEO - Leading strategic vision</li>
<li>Sarah Johnson, CTO - Technical innovation</li>
<li>Michael Brown, CFO - Financial operations</li>
</ul>
<h2>Contact</h2>
<ul>
<li>Email: contact@testcorp.com</li>
<li>Phone: +1-555-123-4567</li>
<li>Address: 123 Innovation Drive, San Francisco, CA 94105</li>
</ul>""",
            metadata={"word_count": 100, "content_type": "about_page"},
            media=[],
            links=[
                {"url": "https://linkedin.com/company/testcorp", "text": "LinkedIn"},
                {"url": "https://twitter.com/testcorp", "text": "Twitter"}
            ]
        ),
        error=None,
        execution_time=2.5
    )


@pytest.fixture
def mock_failed_crawl_response():
    """Mock failed crawl response."""
    return CrawlResponse(
        success=False,
        url="https://testcorp.com/private",
        result=None,
        error="HTTP 403 Forbidden - Access denied",
        execution_time=5.0
    )


@pytest.fixture
def extraction_error_samples():
    """Sample extraction errors for testing."""
    return [
        ExtractionError(
            error_type="SearchError",
            error_message="No search results found for company",
            url=None
        ),
        ExtractionError(
            error_type="CrawlError",
            error_message="Failed to crawl website due to timeout",
            url="https://example.com"
        ),
        ExtractionError(
            error_type="ParseError", 
            error_message="Unable to extract company information from HTML",
            url="https://example.com/about"
        ),
        ExtractionError(
            error_type="ValidationError",
            error_message="Extracted data failed validation checks",
            url="https://example.com"
        )
    ]


@pytest.fixture
def comprehensive_company_data():
    """Comprehensive company data for testing."""
    return {
        "basic_info": {
            "name": "TechCorp Solutions",
            "legal_name": "TechCorp Solutions, Inc.",
            "domain": "techcorp.com",
            "website": "https://techcorp.com",
            "description": "Leading technology company specializing in enterprise software development and cloud solutions.",
            "tagline": "Empowering businesses through innovative technology",
            "industry": "Enterprise Software",
            "sector": CompanySector.TECHNOLOGY,
            "founded_year": 2015,
            "company_size": CompanySize.MEDIUM,
            "employee_count": 340,
            "employee_count_range": "251-500",
            "headquarters": "San Francisco, CA, USA",
            "locations": ["San Francisco, CA", "Austin, TX", "New York, NY"],
            "is_public": False
        },
        "contact": {
            "email": "contact@techcorp.com",
            "phone": "+1-415-555-0123",
            "fax": "+1-415-555-0124",
            "address": "123 Innovation Drive, Suite 400, San Francisco, CA 94105",
            "city": "San Francisco",
            "state": "CA", 
            "country": "United States",
            "postal_code": "94105",
            "additional_emails": ["info@techcorp.com", "support@techcorp.com", "sales@techcorp.com"],
            "additional_phones": ["+1-415-555-0125", "+1-512-555-0126"]
        },
        "social_media": [
            {
                "platform": SocialPlatformType.LINKEDIN,
                "url": "https://linkedin.com/company/techcorp-solutions",
                "username": "techcorp-solutions",
                "followers_count": 12547,
                "verified": True
            },
            {
                "platform": SocialPlatformType.TWITTER,
                "url": "https://twitter.com/techcorp",
                "username": "techcorp",
                "followers_count": 8932,
                "verified": False
            },
            {
                "platform": SocialPlatformType.GITHUB,
                "url": "https://github.com/techcorp",
                "username": "techcorp",
                "followers_count": 2156,
                "verified": None
            }
        ],
        "financials": {
            "revenue": "100M+",
            "revenue_currency": "USD",
            "funding_total": "50M",
            "funding_currency": "USD",
            "last_funding_round": "Series C",
            "last_funding_date": "2023-09-15",
            "valuation": "500M",
            "valuation_currency": "USD",
            "investors": ["Andreessen Horowitz", "Sequoia Capital", "GV (Google Ventures)"]
        },
        "key_personnel": [
            {
                "name": "John Smith",
                "title": "CEO",
                "linkedin_url": "https://linkedin.com/in/john-smith-ceo",
                "email": "john.smith@techcorp.com",
                "bio": "CEO and co-founder with 15+ years of industry experience"
            },
            {
                "name": "Sarah Johnson", 
                "title": "CTO",
                "linkedin_url": "https://linkedin.com/in/sarah-johnson-cto",
                "email": "sarah.johnson@techcorp.com",
                "bio": "CTO leading technical innovation and product development"
            },
            {
                "name": "Michael Brown",
                "title": "CFO",
                "linkedin_url": "https://linkedin.com/in/michael-brown-cfo",
                "bio": "CFO managing financial operations and strategic planning"
            }
        ]
    }


@pytest.fixture
def test_scenarios():
    """Different test scenarios for company extraction."""
    return {
        "success_comprehensive": {
            "request": {
                "company_name": "TechCorp Solutions",
                "domain": "techcorp.com",
                "extraction_mode": ExtractionMode.COMPREHENSIVE,
                "max_pages_to_crawl": 5
            },
            "expected_confidence": 0.8,
            "expected_pages_crawled": 3,
            "should_succeed": True
        },
        "success_contact_focused": {
            "request": {
                "company_name": "ContactCorp",
                "extraction_mode": ExtractionMode.CONTACT_FOCUSED,
                "include_social_media": False,
                "include_financial_data": False,
                "max_pages_to_crawl": 2
            },
            "expected_confidence": 0.6,
            "expected_pages_crawled": 2,
            "should_succeed": True
        },
        "failure_no_results": {
            "request": {
                "company_name": "NonexistentCorp",
                "max_pages_to_crawl": 3
            },
            "expected_confidence": 0.0,
            "expected_pages_crawled": 0,
            "should_succeed": False
        },
        "partial_failure": {
            "request": {
                "company_name": "PartialCorp",
                "max_pages_to_crawl": 5
            },
            "expected_confidence": 0.4,
            "expected_pages_crawled": 2,
            "should_succeed": True  # Partial success
        }
    }


@pytest.fixture
def performance_test_config():
    """Configuration for performance testing."""
    return {
        "max_response_time": 30.0,  # seconds
        "max_memory_usage": 500,    # MB
        "concurrent_requests": 5,
        "timeout_threshold": 10.0,  # seconds
        "error_rate_threshold": 0.1  # 10%
    }


@pytest.fixture
def validation_test_cases():
    """Test cases for input validation."""
    return {
        "valid_requests": [
            {
                "company_name": "ValidCorp",
                "domain": "validcorp.com",
                "extraction_mode": "comprehensive",
                "country": "US",
                "language": "en"
            },
            {
                "company_name": "MinimalCorp"
            },
            {
                "company_name": "ConfiguredCorp",
                "extraction_mode": "contact_focused",
                "max_pages_to_crawl": 1,
                "timeout_seconds": 10
            }
        ],
        "invalid_requests": [
            {
                "company_name": "",  # Empty name
                "error": "min_length"
            },
            {
                "company_name": "TestCorp",
                "country": "usa",  # Invalid format
                "error": "Country code must be 2-letter uppercase"
            },
            {
                "company_name": "TestCorp",
                "language": "EN",  # Invalid format  
                "error": "Language code must be 2-letter lowercase"
            },
            {
                "company_name": "TestCorp",
                "max_pages_to_crawl": 0,  # Too low
                "error": "greater_than_equal"
            },
            {
                "company_name": "TestCorp",
                "max_pages_to_crawl": 25,  # Too high
                "error": "less_than_equal"
            },
            {
                "company_name": "TestCorp",
                "timeout_seconds": 3,  # Too low
                "error": "greater_than_equal" 
            },
            {
                "company_name": "TestCorp",
                "domain": "not..valid",  # Invalid domain
                "error": "Invalid domain format"
            }
        ]
    }


# Async test utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test database setup (if needed for future tests)
@pytest.fixture(scope="session")
def test_database():
    """Set up test database (placeholder for future implementation)."""
    # This could set up a test database for storing test results,
    # performance metrics, or cached test data
    pass


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Cleanup code here (if needed)
    # e.g., clear temp files, reset global state, etc.


# Helper functions for tests
def create_mock_service_with_responses(
    search_response: Optional[SearchResponse] = None,
    crawl_responses: Optional[list] = None,
    extraction_response: Optional[CompanyInformation] = None
) -> CompanyExtractionService:
    """Create a mock service with predefined responses."""
    service = CompanyExtractionService()
    service.serp_service = AsyncMock()
    service.crawl_service = AsyncMock()
    service.company_parser = MagicMock()
    
    if search_response:
        service.serp_service.search = AsyncMock(return_value=search_response)
    
    if crawl_responses:
        service.crawl_service.crawl = AsyncMock(side_effect=crawl_responses)
    
    if extraction_response:
        service.company_parser.extract_company_information = MagicMock(return_value=extraction_response)
    
    return service


def assert_valid_extraction_response(response: CompanyExtractionResponse, should_succeed: bool = True):
    """Assert that extraction response is valid."""
    assert isinstance(response, CompanyExtractionResponse)
    assert isinstance(response.success, bool)
    assert response.success == should_succeed
    assert isinstance(response.company_name, str)
    assert len(response.company_name) > 0
    assert isinstance(response.extraction_metadata, ExtractionMetadata)
    assert isinstance(response.errors, list)
    assert isinstance(response.warnings, list)
    assert response.processing_time >= 0
    
    if should_succeed:
        assert response.company_information is not None
        assert isinstance(response.company_information, CompanyInformation)
        assert 0.0 <= response.company_information.confidence_score <= 1.0
        assert 0.0 <= response.company_information.data_quality_score <= 1.0
        assert 0.0 <= response.company_information.completeness_score <= 1.0


def assert_valid_company_information(company_info: CompanyInformation):
    """Assert that company information is valid."""
    assert isinstance(company_info, CompanyInformation)
    assert isinstance(company_info.basic_info, CompanyBasicInfo)
    assert len(company_info.basic_info.name) > 0
    
    if company_info.contact:
        assert isinstance(company_info.contact, CompanyContact)
    
    assert isinstance(company_info.social_media, list)
    for social in company_info.social_media:
        assert isinstance(social, CompanySocial)
        assert isinstance(social.platform, SocialPlatformType)
    
    if company_info.financials:
        assert isinstance(company_info.financials, CompanyFinancials)
    
    assert isinstance(company_info.key_personnel, list)
    for person in company_info.key_personnel:
        assert isinstance(person, CompanyKeyPersonnel)
        assert len(person.name) > 0
        assert len(person.title) > 0


# Performance testing helpers
class PerformanceTracker:
    """Track performance metrics during tests."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.response_times = []
    
    def start(self):
        """Start performance tracking."""
        import time
        self.start_time = time.time()
    
    def stop(self):
        """Stop performance tracking."""
        import time
        self.end_time = time.time()
    
    def get_duration(self):
        """Get total duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def add_response_time(self, response_time: float):
        """Add a response time measurement."""
        self.response_times.append(response_time)
    
    def get_average_response_time(self):
        """Get average response time."""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0


@pytest.fixture
def performance_tracker():
    """Performance tracking fixture."""
    return PerformanceTracker()