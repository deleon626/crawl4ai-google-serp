"""Test fixtures for company information extraction tests."""

import pytest
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional

from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, CompanyInformation,
    CompanyBasicInfo, CompanyContact, CompanySocial, CompanyFinancials,
    CompanyKeyPersonnel, ExtractionMetadata, ExtractionError, ExtractionMode,
    SocialPlatformType, CompanySize, CompanySector
)
from app.models.serp import SearchResponse, SearchResult
from app.models.crawl import CrawlResponse, CrawlResult


class CompanyTestDataFactory:
    """Factory for creating consistent test data for company extraction tests."""
    
    @staticmethod
    def create_company_request(
        company_name: str = "TestCorp",
        domain: Optional[str] = None,
        extraction_mode: ExtractionMode = ExtractionMode.COMPREHENSIVE,
        **kwargs
    ) -> CompanyInformationRequest:
        """Create a company information request for testing."""
        defaults = {
            "company_name": company_name,
            "domain": domain,
            "extraction_mode": extraction_mode,
            "country": "US",
            "language": "en",
            "include_subsidiaries": False,
            "include_social_media": True,
            "include_financial_data": True,
            "include_contact_info": True,
            "include_key_personnel": True,
            "max_pages_to_crawl": 5,
            "timeout_seconds": 30
        }
        defaults.update(kwargs)
        return CompanyInformationRequest(**defaults)
    
    @staticmethod
    def create_basic_info(
        name: str = "TestCorp",
        **kwargs
    ) -> CompanyBasicInfo:
        """Create basic company information for testing."""
        defaults = {
            "name": name,
            "legal_name": f"{name}, Inc.",
            "domain": f"{name.lower().replace(' ', '')}.com",
            "website": f"https://{name.lower().replace(' ', '')}.com",
            "description": f"{name} is a leading technology company providing innovative solutions.",
            "industry": "Technology",
            "sector": CompanySector.TECHNOLOGY,
            "founded_year": 2015,
            "company_size": CompanySize.MEDIUM,
            "employee_count": 150,
            "employee_count_range": "101-250",
            "headquarters": "San Francisco, CA, USA",
            "locations": ["San Francisco, CA", "Austin, TX"],
            "is_public": False
        }
        defaults.update(kwargs)
        return CompanyBasicInfo(**defaults)
    
    @staticmethod
    def create_contact_info(
        company_name: str = "TestCorp",
        **kwargs
    ) -> CompanyContact:
        """Create contact information for testing."""
        domain = company_name.lower().replace(' ', '') + '.com'
        defaults = {
            "email": f"contact@{domain}",
            "phone": "+1-555-123-4567",
            "fax": "+1-555-123-4568",
            "address": "123 Innovation Drive, Suite 400, San Francisco, CA 94105",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "postal_code": "94105",
            "additional_emails": [f"info@{domain}", f"support@{domain}"],
            "additional_phones": ["+1-555-123-4569"]
        }
        defaults.update(kwargs)
        return CompanyContact(**defaults)
    
    @staticmethod
    def create_social_media(
        company_name: str = "TestCorp",
        platforms: Optional[List[SocialPlatformType]] = None
    ) -> List[CompanySocial]:
        """Create social media profiles for testing."""
        if platforms is None:
            platforms = [
                SocialPlatformType.LINKEDIN,
                SocialPlatformType.TWITTER,
                SocialPlatformType.FACEBOOK,
                SocialPlatformType.GITHUB
            ]
        
        username = company_name.lower().replace(' ', '')
        social_profiles = []
        
        for platform in platforms:
            if platform == SocialPlatformType.LINKEDIN:
                url = f"https://linkedin.com/company/{username}"
            elif platform == SocialPlatformType.TWITTER:
                url = f"https://twitter.com/{username}"
            elif platform == SocialPlatformType.FACEBOOK:
                url = f"https://facebook.com/{username}"
            elif platform == SocialPlatformType.INSTAGRAM:
                url = f"https://instagram.com/{username}"
            elif platform == SocialPlatformType.YOUTUBE:
                url = f"https://youtube.com/c/{username}"
            elif platform == SocialPlatformType.GITHUB:
                url = f"https://github.com/{username}"
            elif platform == SocialPlatformType.TIKTOK:
                url = f"https://tiktok.com/@{username}"
            elif platform == SocialPlatformType.CRUNCHBASE:
                url = f"https://crunchbase.com/organization/{username}"
            else:
                url = f"https://{platform.value}.com/{username}"
            
            social_profiles.append(CompanySocial(
                platform=platform,
                url=url,
                username=username,
                followers_count=10000 + len(social_profiles) * 5000,
                verified=True if platform in [SocialPlatformType.LINKEDIN, SocialPlatformType.TWITTER] else None
            ))
        
        return social_profiles
    
    @staticmethod
    def create_financials(**kwargs) -> CompanyFinancials:
        """Create financial information for testing."""
        defaults = {
            "revenue": "50M",
            "revenue_currency": "USD",
            "funding_total": "25M",
            "funding_currency": "USD",
            "last_funding_round": "Series B",
            "last_funding_date": "2023-06-15",
            "valuation": "200M",
            "valuation_currency": "USD",
            "investors": ["Andreessen Horowitz", "Sequoia Capital", "Y Combinator"]
        }
        defaults.update(kwargs)
        return CompanyFinancials(**defaults)
    
    @staticmethod
    def create_key_personnel(
        company_name: str = "TestCorp"
    ) -> List[CompanyKeyPersonnel]:
        """Create key personnel for testing."""
        return [
            CompanyKeyPersonnel(
                name="John Smith",
                title="CEO",
                linkedin_url="https://linkedin.com/in/john-smith-ceo",
                email=f"john.smith@{company_name.lower().replace(' ', '')}.com",
                bio="CEO and co-founder with 15+ years of industry experience"
            ),
            CompanyKeyPersonnel(
                name="Sarah Johnson",
                title="CTO",
                linkedin_url="https://linkedin.com/in/sarah-johnson-cto",
                email=f"sarah.johnson@{company_name.lower().replace(' ', '')}.com",
                bio="CTO leading technical innovation and product development"
            ),
            CompanyKeyPersonnel(
                name="Michael Brown",
                title="CFO",
                linkedin_url="https://linkedin.com/in/michael-brown-cfo",
                bio="CFO managing financial operations and strategic planning"
            )
        ]
    
    @staticmethod
    def create_company_information(
        company_name: str = "TestCorp",
        include_contact: bool = True,
        include_social: bool = True,
        include_financials: bool = True,
        include_personnel: bool = True,
        **kwargs
    ) -> CompanyInformation:
        """Create complete company information for testing."""
        basic_info = CompanyTestDataFactory.create_basic_info(company_name)
        contact = CompanyTestDataFactory.create_contact_info(company_name) if include_contact else None
        social_media = CompanyTestDataFactory.create_social_media(company_name) if include_social else []
        financials = CompanyTestDataFactory.create_financials() if include_financials else None
        key_personnel = CompanyTestDataFactory.create_key_personnel(company_name) if include_personnel else []
        
        defaults = {
            "basic_info": basic_info,
            "contact": contact,
            "social_media": social_media,
            "financials": financials,
            "key_personnel": key_personnel,
            "confidence_score": 0.85,
            "data_quality_score": 0.80,
            "completeness_score": 0.75
        }
        defaults.update(kwargs)
        return CompanyInformation(**defaults)
    
    @staticmethod
    def create_extraction_metadata(
        pages_crawled: int = 3,
        pages_attempted: int = 5,
        extraction_mode: ExtractionMode = ExtractionMode.COMPREHENSIVE,
        **kwargs
    ) -> ExtractionMetadata:
        """Create extraction metadata for testing."""
        defaults = {
            "pages_crawled": pages_crawled,
            "pages_attempted": pages_attempted,
            "extraction_time": 25.5,
            "sources_found": [
                "https://testcorp.com",
                "https://testcorp.com/about",
                "https://testcorp.com/contact"
            ][:pages_crawled],
            "search_queries_used": [
                "TestCorp company information",
                "TestCorp contact details",
                "TestCorp about us"
            ],
            "extraction_mode_used": extraction_mode
        }
        defaults.update(kwargs)
        return ExtractionMetadata(**defaults)
    
    @staticmethod
    def create_extraction_response(
        company_name: str = "TestCorp",
        success: bool = True,
        include_company_info: bool = True,
        errors: Optional[List[ExtractionError]] = None,
        warnings: Optional[List[str]] = None,
        **kwargs
    ) -> CompanyExtractionResponse:
        """Create extraction response for testing."""
        company_info = None
        if include_company_info and success:
            company_info = CompanyTestDataFactory.create_company_information(company_name)
        
        defaults = {
            "request_id": f"req_{company_name.lower().replace(' ', '')}_123456",
            "company_name": company_name,
            "success": success,
            "company_information": company_info,
            "extraction_metadata": CompanyTestDataFactory.create_extraction_metadata(),
            "errors": errors or [],
            "warnings": warnings or [],
            "processing_time": 27.8
        }
        defaults.update(kwargs)
        return CompanyExtractionResponse(**defaults)
    
    @staticmethod
    def create_search_response(
        company_name: str = "TestCorp",
        result_count: int = 5,
        include_social: bool = True,
        include_contact: bool = True,
        **kwargs
    ) -> SearchResponse:
        """Create SERP search response for testing."""
        domain = f"{company_name.lower().replace(' ', '')}.com"
        base_url = f"https://{domain}"
        
        organic_results = [
            SearchResult(
                rank=1,
                title=f"{company_name} - Home",
                url=base_url,
                description=f"{company_name} official website and company information."
            ),
            SearchResult(
                rank=2,
                title=f"{company_name} - About Us",
                url=f"{base_url}/about",
                description=f"Learn more about {company_name}'s mission, history, and team."
            )
        ]
        
        if include_contact:
            organic_results.append(SearchResult(
                rank=len(organic_results) + 1,
                title=f"{company_name} - Contact Information",
                url=f"{base_url}/contact",
                description=f"Get in touch with {company_name} for inquiries and support."
            ))
        
        if include_social:
            username = company_name.lower().replace(' ', '')
            organic_results.extend([
                SearchResult(
                    rank=len(organic_results) + 1,
                    title=f"{company_name} | LinkedIn",
                    url=f"https://linkedin.com/company/{username}",
                    description=f"{company_name} company page on LinkedIn."
                ),
                SearchResult(
                    rank=len(organic_results) + 1,
                    title=f"{company_name} on Twitter",
                    url=f"https://twitter.com/{username}",
                    description=f"Follow {company_name} for company updates and insights."
                )
            ])
        
        # Trim to requested result count
        organic_results = organic_results[:result_count]
        
        defaults = {
            "query": f"{company_name} company information",
            "results_count": len(organic_results),
            "organic_results": organic_results,
            "search_metadata": {
                "total_results": len(organic_results) * 1000,
                "time_taken": 0.5
            }
        }
        defaults.update(kwargs)
        return SearchResponse(**defaults)
    
    @staticmethod
    def create_crawl_response(
        url: str,
        success: bool = True,
        content_type: str = "about_page",
        company_name: str = "TestCorp",
        **kwargs
    ) -> CrawlResponse:
        """Create crawl response for testing."""
        if not success:
            defaults = {
                "success": False,
                "url": url,
                "result": None,
                "error": "Failed to crawl page",
                "execution_time": 5.0
            }
            defaults.update(kwargs)
            return CrawlResponse(**defaults)
        
        # Generate content based on type
        if content_type == "about_page":
            title = f"{company_name} - About Us"
            markdown = f"""# {company_name}

{company_name} is a leading technology company founded in 2015, specializing in innovative software solutions.

## Our Mission
We provide cutting-edge technology solutions that help businesses transform and grow.

## Company Information
- **Founded**: 2015
- **Employees**: 150+ team members
- **Headquarters**: San Francisco, California
- **Industry**: Technology & Software Development

## Leadership Team
- John Smith, CEO - Leading our strategic vision
- Sarah Johnson, CTO - Overseeing technical innovation
- Michael Brown, CFO - Managing financial operations

Contact us at contact@{company_name.lower().replace(' ', '')}.com or +1-555-123-4567.
"""
            
            html = f"""<h1>{company_name}</h1>
<p>{company_name} is a leading technology company founded in 2015, specializing in innovative software solutions.</p>
<h2>Our Mission</h2>
<p>We provide cutting-edge technology solutions that help businesses transform and grow.</p>
<h2>Company Information</h2>
<ul>
<li><strong>Founded</strong>: 2015</li>
<li><strong>Employees</strong>: 150+ team members</li>
<li><strong>Headquarters</strong>: San Francisco, California</li>
<li><strong>Industry</strong>: Technology &amp; Software Development</li>
</ul>
<h2>Leadership Team</h2>
<ul>
<li>John Smith, CEO - Leading our strategic vision</li>
<li>Sarah Johnson, CTO - Overseeing technical innovation</li>
<li>Michael Brown, CFO - Managing financial operations</li>
</ul>
<p>Contact us at contact@{company_name.lower().replace(' ', '')}.com or +1-555-123-4567.</p>"""
            
        elif content_type == "contact_page":
            title = f"{company_name} - Contact Us"
            markdown = f"""# Contact {company_name}

## Get in Touch
We'd love to hear from you. Contact us using the information below.

## Contact Details
- **Email**: contact@{company_name.lower().replace(' ', '')}.com
- **Phone**: +1-555-123-4567
- **Address**: 123 Innovation Drive, San Francisco, CA 94105

## Office Hours
Monday - Friday: 9:00 AM - 6:00 PM PST
"""
            
            html = f"""<h1>Contact {company_name}</h1>
<h2>Get in Touch</h2>
<p>We'd love to hear from you. Contact us using the information below.</p>
<h2>Contact Details</h2>
<ul>
<li><strong>Email</strong>: contact@{company_name.lower().replace(' ', '')}.com</li>
<li><strong>Phone</strong>: +1-555-123-4567</li>
<li><strong>Address</strong>: 123 Innovation Drive, San Francisco, CA 94105</li>
</ul>"""
            
        else:  # generic page
            title = f"{company_name} - Information"
            markdown = f"# {company_name}\n\nGeneric page content for {company_name}."
            html = f"<h1>{company_name}</h1><p>Generic page content for {company_name}.</p>"
        
        result = CrawlResult(
            url=url,
            title=title,
            markdown=markdown,
            cleaned_html=html,
            metadata={"word_count": len(markdown.split()), "content_type": content_type},
            media=[],
            links=[]
        )
        
        defaults = {
            "success": True,
            "url": url,
            "result": result,
            "error": None,
            "execution_time": 2.5
        }
        defaults.update(kwargs)
        return CrawlResponse(**defaults)


# Pytest fixtures
@pytest.fixture
def company_factory():
    """Provide company test data factory."""
    return CompanyTestDataFactory


@pytest.fixture
def sample_company_request():
    """Sample company information request."""
    return CompanyTestDataFactory.create_company_request()


@pytest.fixture
def comprehensive_company_request():
    """Comprehensive company information request."""
    return CompanyTestDataFactory.create_company_request(
        company_name="TechCorp Solutions",
        domain="techcorp.com",
        extraction_mode=ExtractionMode.COMPREHENSIVE,
        include_subsidiaries=True,
        max_pages_to_crawl=10,
        timeout_seconds=60
    )


@pytest.fixture
def contact_focused_request():
    """Contact-focused extraction request."""
    return CompanyTestDataFactory.create_company_request(
        company_name="ContactCorp",
        extraction_mode=ExtractionMode.CONTACT_FOCUSED,
        include_social_media=False,
        include_financial_data=False,
        include_key_personnel=False,
        max_pages_to_crawl=3
    )


@pytest.fixture
def sample_company_info():
    """Sample company information."""
    return CompanyTestDataFactory.create_company_information()


@pytest.fixture
def sample_extraction_response():
    """Sample extraction response."""
    return CompanyTestDataFactory.create_extraction_response()


@pytest.fixture
def sample_search_response():
    """Sample SERP search response."""
    return CompanyTestDataFactory.create_search_response()


@pytest.fixture
def failed_extraction_response():
    """Failed extraction response with errors."""
    errors = [
        ExtractionError(
            error_type="SearchError",
            error_message="No search results found",
            timestamp=datetime.now(UTC)
        ),
        ExtractionError(
            error_type="CrawlError", 
            error_message="Failed to crawl website",
            url="https://failedcorp.com",
            timestamp=datetime.now(UTC)
        )
    ]
    
    return CompanyTestDataFactory.create_extraction_response(
        company_name="FailedCorp",
        success=False,
        include_company_info=False,
        errors=errors,
        warnings=["Limited data available", "Extraction incomplete"]
    )


@pytest.fixture
def mock_html_samples():
    """HTML samples for different page types."""
    return {
        'about_page': """
        <html>
            <head>
                <title>TestCorp - About Us</title>
                <meta name="description" content="TestCorp is a leading technology company providing innovative solutions.">
            </head>
            <body>
                <h1>About TestCorp</h1>
                <p>TestCorp is a leading technology company founded in 2015.</p>
                <p>We have 150+ employees and are headquartered in San Francisco, CA.</p>
                <p>Contact us at contact@testcorp.com or +1-555-123-4567.</p>
            </body>
        </html>
        """,
        
        'contact_page': """
        <html>
            <body>
                <h1>Contact TestCorp</h1>
                <div class="contact-info">
                    <p>Email: contact@testcorp.com</p>
                    <p>Phone: +1-555-123-4567</p>
                    <p>Address: 123 Innovation Drive, San Francisco, CA 94105</p>
                </div>
            </body>
        </html>
        """,
        
        'social_page': """
        <html>
            <body>
                <div class="social-links">
                    <a href="https://linkedin.com/company/testcorp">LinkedIn</a>
                    <a href="https://twitter.com/testcorp">Twitter</a>
                    <a href="https://github.com/testcorp">GitHub</a>
                </div>
            </body>
        </html>
        """,
        
        'malformed_html': """
        <html>
            <head>
                <title>Malformed TestCorp
            <body>
                <h1>TestCorp
                <p>Unclosed tags and issues
                <div><span>Nested without closing
        """
    }


# Mock data collections
SAMPLE_COMPANIES = {
    "OpenAI": {
        "domain": "openai.com",
        "industry": "Artificial Intelligence",
        "founded": 2015,
        "headquarters": "San Francisco, CA"
    },
    "Microsoft": {
        "domain": "microsoft.com", 
        "industry": "Technology",
        "founded": 1975,
        "headquarters": "Redmond, WA"
    },
    "Stripe": {
        "domain": "stripe.com",
        "industry": "Financial Technology",
        "founded": 2010,
        "headquarters": "San Francisco, CA"
    }
}


ERROR_SCENARIOS = {
    "search_timeout": {
        "error_type": "BrightDataTimeoutError",
        "message": "Search request timed out after 30 seconds"
    },
    "search_rate_limit": {
        "error_type": "BrightDataRateLimitError", 
        "message": "Rate limit exceeded for search API"
    },
    "crawl_forbidden": {
        "error_type": "CrawlError",
        "message": "HTTP 403 Forbidden - Access denied"
    },
    "parsing_error": {
        "error_type": "ParseError",
        "message": "Failed to parse HTML content"
    }
}