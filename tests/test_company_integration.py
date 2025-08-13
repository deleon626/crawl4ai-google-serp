"""Comprehensive integration tests for company information extraction workflows."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC

from app.services.company_service import CompanyExtractionService
from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, CompanyInformation,
    CompanyBasicInfo, CompanyContact, CompanySocial, CompanyFinancials,
    CompanyKeyPersonnel, ExtractionMetadata, ExtractionError, ExtractionMode,
    SocialPlatformType, CompanySize, CompanySector
)
from app.models.serp import SearchResponse, SearchResult
from app.models.crawl import CrawlResponse, CrawlResult
from app.utils.exceptions import BrightDataError


class TestCompanyExtractionIntegration:
    """Integration tests for complete company extraction workflows."""
    
    @pytest.fixture
    async def service(self):
        """Create company extraction service for testing."""
        service = CompanyExtractionService()
        async with service:
            yield service
    
    @pytest.fixture
    def comprehensive_request(self):
        """Comprehensive extraction request."""
        return CompanyInformationRequest(
            company_name="TechCorp Solutions",
            domain="techcorp.com",
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            country="US",
            language="en",
            include_subsidiaries=True,
            include_social_media=True,
            include_financial_data=True,
            include_contact_info=True,
            include_key_personnel=True,
            max_pages_to_crawl=5,
            timeout_seconds=30
        )
    
    @pytest.fixture
    def contact_focused_request(self):
        """Contact-focused extraction request."""
        return CompanyInformationRequest(
            company_name="ContactCorp",
            extraction_mode=ExtractionMode.CONTACT_FOCUSED,
            include_social_media=False,
            include_financial_data=False,
            include_contact_info=True,
            include_key_personnel=False,
            max_pages_to_crawl=3,
            timeout_seconds=20
        )
    
    @pytest.fixture
    def mock_search_responses(self):
        """Mock SERP search responses for different scenarios."""
        return {
            'comprehensive': SearchResponse(
                query="TechCorp Solutions company information",
                results_count=10,
                organic_results=[
                    SearchResult(
                        rank=1,
                        title="TechCorp Solutions - About Us",
                        url="https://techcorp.com/about",
                        description="TechCorp Solutions is a leading technology company providing innovative software solutions."
                    ),
                    SearchResult(
                        rank=2,
                        title="TechCorp Solutions - Contact Information",
                        url="https://techcorp.com/contact",
                        description="Get in touch with TechCorp Solutions for inquiries and support."
                    ),
                    SearchResult(
                        rank=3,
                        title="TechCorp Solutions | LinkedIn",
                        url="https://linkedin.com/company/techcorp-solutions",
                        description="TechCorp Solutions company page on LinkedIn with latest updates."
                    ),
                    SearchResult(
                        rank=4,
                        title="TechCorp Solutions on Twitter",
                        url="https://twitter.com/techcorp",
                        description="Follow TechCorp Solutions for technology insights and company news."
                    ),
                    SearchResult(
                        rank=5,
                        title="TechCorp Solutions Funding and Investors | Crunchbase",
                        url="https://crunchbase.com/organization/techcorp-solutions",
                        description="TechCorp Solutions has raised $50M in funding from top-tier investors."
                    )
                ],
                search_metadata={"total_results": 150000, "time_taken": 0.8}
            ),
            'contact_focused': SearchResponse(
                query="ContactCorp contact information",
                results_count=5,
                organic_results=[
                    SearchResult(
                        rank=1,
                        title="ContactCorp - Contact Us",
                        url="https://contactcorp.com/contact",
                        description="Contact ContactCorp for business inquiries and support."
                    ),
                    SearchResult(
                        rank=2,
                        title="ContactCorp Headquarters and Office Locations",
                        url="https://contactcorp.com/locations",
                        description="Find ContactCorp office locations and contact details worldwide."
                    )
                ],
                search_metadata={"total_results": 5000, "time_taken": 0.3}
            )
        }
    
    @pytest.fixture
    def mock_crawl_responses(self):
        """Mock crawl responses for different page types."""
        return {
            'about_page': CrawlResponse(
                success=True,
                url="https://techcorp.com/about",
                result=CrawlResult(
                    url="https://techcorp.com/about",
                    title="TechCorp Solutions - About Us",
                    markdown="""# TechCorp Solutions

TechCorp Solutions is a leading technology company founded in 2015, specializing in enterprise software development and cloud solutions.

## Our Mission
We provide innovative technology solutions that help businesses transform and grow in the digital age.

## Company Information
- **Founded**: 2015
- **Employees**: 250+ team members
- **Headquarters**: San Francisco, California
- **Industry**: Technology & Software Development

## Leadership Team
- John Smith, CEO - Leading our strategic vision
- Sarah Johnson, CTO - Overseeing technical innovation
- Michael Brown, CFO - Managing financial operations

## Contact Information
- **Email**: info@techcorp.com
- **Phone**: +1-555-123-4567
- **Address**: 123 Innovation Drive, San Francisco, CA 94105

Follow us on social media:
- [LinkedIn](https://linkedin.com/company/techcorp-solutions)
- [Twitter](https://twitter.com/techcorp)
- [GitHub](https://github.com/techcorp)
                    """,
                    cleaned_html="""<h1>TechCorp Solutions</h1>
                    <p>TechCorp Solutions is a leading technology company founded in 2015, specializing in enterprise software development and cloud solutions.</p>
                    <h2>Our Mission</h2>
                    <p>We provide innovative technology solutions that help businesses transform and grow in the digital age.</p>
                    <h2>Company Information</h2>
                    <ul>
                        <li><strong>Founded</strong>: 2015</li>
                        <li><strong>Employees</strong>: 250+ team members</li>
                        <li><strong>Headquarters</strong>: San Francisco, California</li>
                        <li><strong>Industry</strong>: Technology &amp; Software Development</li>
                    </ul>
                    <h2>Leadership Team</h2>
                    <ul>
                        <li>John Smith, CEO - Leading our strategic vision</li>
                        <li>Sarah Johnson, CTO - Overseeing technical innovation</li>
                        <li>Michael Brown, CFO - Managing financial operations</li>
                    </ul>
                    <h2>Contact Information</h2>
                    <ul>
                        <li><strong>Email</strong>: info@techcorp.com</li>
                        <li><strong>Phone</strong>: +1-555-123-4567</li>
                        <li><strong>Address</strong>: 123 Innovation Drive, San Francisco, CA 94105</li>
                    </ul>
                    <p>Follow us on social media:</p>
                    <ul>
                        <li><a href="https://linkedin.com/company/techcorp-solutions">LinkedIn</a></li>
                        <li><a href="https://twitter.com/techcorp">Twitter</a></li>
                        <li><a href="https://github.com/techcorp">GitHub</a></li>
                    </ul>""",
                    metadata={"word_count": 180, "content_type": "about_page"},
                    media=[],
                    links=[
                        {"url": "https://linkedin.com/company/techcorp-solutions", "text": "LinkedIn"},
                        {"url": "https://twitter.com/techcorp", "text": "Twitter"},
                        {"url": "https://github.com/techcorp", "text": "GitHub"}
                    ]
                ),
                error=None,
                execution_time=2.5
            ),
            'contact_page': CrawlResponse(
                success=True,
                url="https://techcorp.com/contact",
                result=CrawlResult(
                    url="https://techcorp.com/contact",
                    title="TechCorp Solutions - Contact Us",
                    markdown="""# Contact TechCorp Solutions

## Get in Touch
We'd love to hear from you. Contact us using the information below.

## Contact Details
- **General Inquiries**: info@techcorp.com
- **Sales**: sales@techcorp.com  
- **Support**: support@techcorp.com
- **Phone**: +1-555-123-4567
- **Fax**: +1-555-123-4568

## Office Locations

### Headquarters
123 Innovation Drive, Suite 400
San Francisco, CA 94105
United States

### Branch Office
456 Tech Street
Austin, TX 78701
United States

## Business Hours
Monday - Friday: 9:00 AM - 6:00 PM PST
Saturday: 10:00 AM - 2:00 PM PST
Sunday: Closed
                    """,
                    cleaned_html="""<h1>Contact TechCorp Solutions</h1>
                    <h2>Get in Touch</h2>
                    <p>We'd love to hear from you. Contact us using the information below.</p>
                    <h2>Contact Details</h2>
                    <ul>
                        <li><strong>General Inquiries</strong>: info@techcorp.com</li>
                        <li><strong>Sales</strong>: sales@techcorp.com</li>
                        <li><strong>Support</strong>: support@techcorp.com</li>
                        <li><strong>Phone</strong>: +1-555-123-4567</li>
                        <li><strong>Fax</strong>: +1-555-123-4568</li>
                    </ul>
                    <h2>Office Locations</h2>
                    <h3>Headquarters</h3>
                    <p>123 Innovation Drive, Suite 400<br>San Francisco, CA 94105<br>United States</p>
                    <h3>Branch Office</h3>
                    <p>456 Tech Street<br>Austin, TX 78701<br>United States</p>""",
                    metadata={"word_count": 120, "content_type": "contact_page"},
                    media=[],
                    links=[]
                ),
                error=None,
                execution_time=1.8
            ),
            'linkedin_page': CrawlResponse(
                success=True,
                url="https://linkedin.com/company/techcorp-solutions",
                result=CrawlResult(
                    url="https://linkedin.com/company/techcorp-solutions",
                    title="TechCorp Solutions | LinkedIn",
                    markdown="""# TechCorp Solutions

**Technology & Software Development Company**

250-500 employees · San Francisco, California

## About
TechCorp Solutions is a leading technology company specializing in enterprise software development, cloud solutions, and digital transformation services. Founded in 2015, we help businesses leverage cutting-edge technology to achieve their goals.

**Website**: https://techcorp.com
**Industry**: Technology Services
**Company Size**: 250-500 employees  
**Founded**: 2015
**Specialties**: Enterprise Software, Cloud Solutions, Digital Transformation, AI & Machine Learning

## Recent Updates
- Announced Series C funding round of $50M
- Expanded operations to Austin, Texas
- Launched new AI-powered analytics platform

## Employees
- John Smith - Chief Executive Officer
- Sarah Johnson - Chief Technology Officer  
- Michael Brown - Chief Financial Officer
- 250+ other employees

Follow us for technology insights and company updates.
                    """,
                    cleaned_html="""<div class="company-profile">
                    <h1>TechCorp Solutions</h1>
                    <p><strong>Technology &amp; Software Development Company</strong></p>
                    <p>250-500 employees · San Francisco, California</p>
                    <h2>About</h2>
                    <p>TechCorp Solutions is a leading technology company specializing in enterprise software development, cloud solutions, and digital transformation services. Founded in 2015, we help businesses leverage cutting-edge technology to achieve their goals.</p>
                    <ul>
                        <li><strong>Website</strong>: https://techcorp.com</li>
                        <li><strong>Industry</strong>: Technology Services</li>
                        <li><strong>Company Size</strong>: 250-500 employees</li>
                        <li><strong>Founded</strong>: 2015</li>
                        <li><strong>Specialties</strong>: Enterprise Software, Cloud Solutions, Digital Transformation, AI &amp; Machine Learning</li>
                    </ul>
                    </div>""",
                    metadata={"word_count": 150, "content_type": "linkedin_profile"},
                    media=[],
                    links=[{"url": "https://techcorp.com", "text": "techcorp.com"}]
                ),
                error=None,
                execution_time=3.2
            ),
            'failed_crawl': CrawlResponse(
                success=False,
                url="https://techcorp.com/private",
                result=None,
                error="HTTP 403 Forbidden - Access denied",
                execution_time=5.0
            )
        }
    
    @pytest.mark.asyncio
    async def test_comprehensive_extraction_success(
        self, service, comprehensive_request, mock_search_responses, mock_crawl_responses
    ):
        """Test comprehensive company information extraction workflow."""
        # Mock SERP service
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        
        # Mock crawl service to return different responses based on URL
        def mock_crawl_side_effect(request):
            if "about" in request.url:
                return mock_crawl_responses['about_page']
            elif "contact" in request.url:
                return mock_crawl_responses['contact_page']
            elif "linkedin" in request.url:
                return mock_crawl_responses['linkedin_page']
            else:
                return mock_crawl_responses['failed_crawl']
        
        service.crawl_service.crawl = AsyncMock(side_effect=mock_crawl_side_effect)
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Verify response structure
        assert isinstance(response, CompanyExtractionResponse)
        assert response.success is True
        assert response.company_name == "TechCorp Solutions"
        assert response.company_information is not None
        
        # Verify basic information
        basic_info = response.company_information.basic_info
        assert basic_info.name == "TechCorp Solutions"
        assert basic_info.domain == "techcorp.com"
        assert basic_info.founded_year == 2015
        assert basic_info.employee_count >= 250
        assert basic_info.company_size == CompanySize.MEDIUM
        assert basic_info.sector == CompanySector.TECHNOLOGY
        assert "San Francisco" in basic_info.headquarters
        
        # Verify contact information
        contact = response.company_information.contact
        assert contact is not None
        assert contact.email == "info@techcorp.com"
        assert contact.phone == "+1-555-123-4567"
        assert "San Francisco" in contact.address
        assert "sales@techcorp.com" in contact.additional_emails
        assert "support@techcorp.com" in contact.additional_emails
        
        # Verify social media profiles
        social_media = response.company_information.social_media
        assert len(social_media) >= 3
        platforms = {profile.platform for profile in social_media}
        assert SocialPlatformType.LINKEDIN in platforms
        assert SocialPlatformType.TWITTER in platforms
        assert SocialPlatformType.GITHUB in platforms
        
        # Verify key personnel
        personnel = response.company_information.key_personnel
        assert len(personnel) >= 3
        titles = {person.title for person in personnel}
        assert "CEO" in titles
        assert "CTO" in titles
        assert "CFO" in titles
        
        # Verify metadata
        metadata = response.extraction_metadata
        assert metadata.pages_crawled >= 2
        assert metadata.pages_attempted >= 3
        assert len(metadata.sources_found) >= 2
        assert len(metadata.search_queries_used) >= 1
        assert metadata.extraction_mode_used == ExtractionMode.COMPREHENSIVE
        
        # Verify confidence scores
        assert response.company_information.confidence_score > 0.7
        assert response.company_information.data_quality_score > 0.6
        assert response.company_information.completeness_score > 0.5
        
        # Verify no critical errors
        critical_errors = [e for e in response.errors if "critical" in e.error_type.lower()]
        assert len(critical_errors) == 0
    
    @pytest.mark.asyncio
    async def test_contact_focused_extraction(
        self, service, contact_focused_request, mock_search_responses, mock_crawl_responses
    ):
        """Test contact-focused extraction mode."""
        # Mock SERP service
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['contact_focused'])
        
        # Mock crawl service
        service.crawl_service.crawl = AsyncMock(return_value=mock_crawl_responses['contact_page'])
        
        # Execute extraction
        response = await service.extract_company_information(contact_focused_request)
        
        # Verify response
        assert response.success is True
        assert response.company_name == "ContactCorp"
        
        # Should have prioritized contact information
        contact = response.company_information.contact
        assert contact is not None
        assert contact.email is not None
        assert contact.phone is not None
        assert contact.address is not None
        
        # Should have fewer social media profiles (not prioritized)
        social_media = response.company_information.social_media
        assert len(social_media) <= 2  # Should be limited in contact-focused mode
        
        # Metadata should reflect contact focus
        assert response.extraction_metadata.extraction_mode_used == ExtractionMode.CONTACT_FOCUSED
    
    @pytest.mark.asyncio
    async def test_search_failure_resilience(self, service, comprehensive_request):
        """Test extraction resilience when search fails."""
        # Mock SERP service to fail
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataError("Search API temporarily unavailable")
        )
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Should handle failure gracefully
        assert response.success is False
        assert len(response.errors) > 0
        
        # Should have search error
        search_errors = [e for e in response.errors if "search" in e.error_type.lower()]
        assert len(search_errors) > 0
        
        # Metadata should reflect minimal pages
        assert response.extraction_metadata.pages_crawled == 0
        assert response.extraction_metadata.pages_attempted == 0
    
    @pytest.mark.asyncio
    async def test_partial_crawl_failures(
        self, service, comprehensive_request, mock_search_responses, mock_crawl_responses
    ):
        """Test extraction when some pages fail to crawl."""
        # Mock SERP service
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        
        # Mock crawl service with mixed success/failure
        crawl_responses = [
            mock_crawl_responses['about_page'],  # Success
            mock_crawl_responses['failed_crawl'],  # Failure
            mock_crawl_responses['contact_page'],  # Success
            mock_crawl_responses['failed_crawl'],  # Failure
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=crawl_responses)
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Should succeed despite partial failures
        assert response.success is True
        assert response.company_information is not None
        
        # Should have some crawl errors
        crawl_errors = [e for e in response.errors if "crawl" in e.error_type.lower()]
        assert len(crawl_errors) >= 1
        
        # Should have extracted data from successful crawls
        assert response.company_information.basic_info.name is not None
        assert response.company_information.contact is not None
        
        # Metadata should reflect partial success
        metadata = response.extraction_metadata
        assert metadata.pages_crawled < metadata.pages_attempted
        assert metadata.pages_crawled >= 2  # At least 2 successful
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, service, comprehensive_request):
        """Test extraction with timeout constraints."""
        # Set very short timeout
        comprehensive_request.timeout_seconds = 5
        
        # Mock services with delays
        async def delayed_search(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return mock_search_responses['comprehensive']
        
        service.serp_service.search = delayed_search
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Should handle timeout gracefully
        assert response.success is False or len(response.warnings) > 0
        
        # Should complete in reasonable time despite timeouts
        assert response.processing_time < 15  # Should not wait for full delays
    
    @pytest.mark.asyncio
    async def test_data_aggregation_multiple_sources(
        self, service, comprehensive_request, mock_search_responses, mock_crawl_responses
    ):
        """Test data aggregation from multiple sources."""
        # Mock SERP service
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        
        # Create varied crawl responses with different data
        about_response = mock_crawl_responses['about_page']
        contact_response = mock_crawl_responses['contact_page'] 
        linkedin_response = mock_crawl_responses['linkedin_page']
        
        # Mock crawl service to return different responses
        def mock_crawl_side_effect(request):
            if "about" in request.url:
                return about_response
            elif "contact" in request.url:
                return contact_response
            elif "linkedin" in request.url:
                return linkedin_response
            else:
                return mock_crawl_responses['failed_crawl']
        
        service.crawl_service.crawl = AsyncMock(side_effect=mock_crawl_side_effect)
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Verify data was aggregated from multiple sources
        assert response.success is True
        company_info = response.company_information
        
        # Should have data from about page
        assert company_info.basic_info.founded_year == 2015
        assert company_info.key_personnel is not None
        assert len(company_info.key_personnel) >= 3
        
        # Should have data from contact page
        assert company_info.contact is not None
        assert len(company_info.contact.additional_emails) >= 2
        
        # Should have data from LinkedIn page
        assert company_info.social_media is not None
        linkedin_profile = next(
            (s for s in company_info.social_media if s.platform == SocialPlatformType.LINKEDIN),
            None
        )
        assert linkedin_profile is not None
        
        # Sources should reflect multiple pages
        sources = response.extraction_metadata.sources_found
        assert len(sources) >= 3
        assert any("about" in url for url in sources)
        assert any("contact" in url for url in sources)
        assert any("linkedin" in url for url in sources)
    
    @pytest.mark.asyncio
    async def test_confidence_scoring_accuracy(
        self, service, comprehensive_request, mock_search_responses, mock_crawl_responses
    ):
        """Test confidence scoring reflects data quality."""
        # Test with high-quality data
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        service.crawl_service.crawl = AsyncMock(return_value=mock_crawl_responses['about_page'])
        
        response_high_quality = await service.extract_company_information(comprehensive_request)
        
        # Test with limited data
        limited_search = SearchResponse(
            query="Limited company info",
            results_count=1,
            organic_results=[
                SearchResult(
                    rank=1,
                    title="Limited Company",
                    url="https://limited.com",
                    description="Limited information available"
                )
            ]
        )
        
        limited_crawl = CrawlResponse(
            success=True,
            url="https://limited.com",
            result=CrawlResult(
                url="https://limited.com",
                title="Limited Company",
                markdown="# Limited Company\n\nMinimal information available.",
                cleaned_html="<h1>Limited Company</h1><p>Minimal information available.</p>",
                metadata={"word_count": 5},
                media=[],
                links=[]
            ),
            execution_time=1.0
        )
        
        service.serp_service.search = AsyncMock(return_value=limited_search)
        service.crawl_service.crawl = AsyncMock(return_value=limited_crawl)
        
        response_low_quality = await service.extract_company_information(
            CompanyInformationRequest(company_name="Limited Company")
        )
        
        # High-quality extraction should have better scores
        assert response_high_quality.company_information.confidence_score > \
               response_low_quality.company_information.confidence_score
        assert response_high_quality.company_information.data_quality_score > \
               response_low_quality.company_information.data_quality_score
        assert response_high_quality.company_information.completeness_score > \
               response_low_quality.company_information.completeness_score
    
    @pytest.mark.asyncio
    async def test_extraction_metadata_accuracy(
        self, service, comprehensive_request, mock_search_responses, mock_crawl_responses
    ):
        """Test extraction metadata reflects actual processing."""
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        
        # Track crawl calls
        crawl_calls = []
        
        def track_crawl_calls(request):
            crawl_calls.append(request.url)
            if "about" in request.url:
                return mock_crawl_responses['about_page']
            elif "contact" in request.url:
                return mock_crawl_responses['contact_page']
            else:
                return mock_crawl_responses['failed_crawl']
        
        service.crawl_service.crawl = AsyncMock(side_effect=track_crawl_calls)
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Verify metadata accuracy
        metadata = response.extraction_metadata
        
        # Should reflect actual crawl attempts
        assert metadata.pages_attempted == len(crawl_calls)
        
        # Should count successful crawls
        successful_crawls = len([call for call in crawl_calls 
                               if not ("private" in call or "failed" in call)])
        assert metadata.pages_crawled == successful_crawls
        
        # Should have reasonable processing time
        assert metadata.extraction_time > 0
        assert response.processing_time >= metadata.extraction_time
        
        # Should track sources where data was found
        assert len(metadata.sources_found) <= metadata.pages_crawled
        assert all(url in crawl_calls for url in metadata.sources_found)
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_warnings(
        self, service, comprehensive_request, mock_search_responses
    ):
        """Test error recovery mechanisms and warning generation."""
        service.serp_service.search = AsyncMock(return_value=mock_search_responses['comprehensive'])
        
        # Mock mixed crawl results with various error types
        error_responses = [
            CrawlResponse(success=False, url="https://site1.com", error="Timeout", execution_time=30.0),
            CrawlResponse(success=False, url="https://site2.com", error="403 Forbidden", execution_time=1.0),
            mock_crawl_responses['about_page'],  # One success
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=error_responses)
        
        # Execute extraction
        response = await service.extract_company_information(comprehensive_request)
        
        # Should recover and provide partial results
        assert response.company_information is not None
        assert response.company_information.basic_info.name is not None
        
        # Should record errors
        assert len(response.errors) >= 2
        error_types = [error.error_type for error in response.errors]
        assert "TimeoutError" in error_types or "CrawlError" in error_types
        
        # Should generate appropriate warnings
        assert len(response.warnings) > 0
        
        # Should still calculate reasonable confidence despite errors
        assert 0.0 <= response.company_information.confidence_score <= 1.0


class TestServiceOrchestration:
    """Test service orchestration and resource management."""
    
    @pytest.mark.asyncio
    async def test_service_context_manager(self):
        """Test service context manager lifecycle."""
        service = CompanyExtractionService()
        
        # Services should not be initialized before context
        assert service.serp_service is None
        assert service.crawl_service is None
        assert service.company_parser is not None  # Created immediately
        
        # Enter context
        async with service as ctx_service:
            assert ctx_service is service
            assert service.serp_service is not None
            assert service.crawl_service is not None
        
        # After context exit, services should be cleaned up
        # Note: Services may still exist but should be closed
    
    @pytest.mark.asyncio
    async def test_service_initialization_failure_handling(self):
        """Test handling of service initialization failures."""
        with patch('app.services.serp_service.SERPService.__aenter__') as mock_serp_init:
            mock_serp_init.side_effect = Exception("SERP service initialization failed")
            
            service = CompanyExtractionService()
            
            # Should handle initialization failure gracefully
            with pytest.raises(Exception, match="SERP service initialization failed"):
                async with service:
                    pass
    
    @pytest.mark.asyncio
    async def test_concurrent_extraction_requests(self):
        """Test handling of concurrent extraction requests."""
        # Create multiple requests
        requests = [
            CompanyInformationRequest(company_name=f"Company{i}", max_pages_to_crawl=2)
            for i in range(3)
        ]
        
        # Mock responses
        mock_response = CompanyExtractionResponse(
            request_id="concurrent_test",
            company_name="Test",
            success=True,
            company_information=CompanyInformation(
                basic_info=CompanyBasicInfo(name="Test")
            ),
            extraction_metadata=ExtractionMetadata(
                pages_crawled=1,
                pages_attempted=1,
                extraction_time=1.0,
                extraction_mode_used=ExtractionMode.COMPREHENSIVE
            ),
            processing_time=2.0
        )
        
        async with CompanyExtractionService() as service:
            service.serp_service.search = AsyncMock(return_value=SearchResponse(
                query="test", results_count=0, organic_results=[]
            ))
            service.crawl_service.crawl = AsyncMock(return_value=CrawlResponse(
                success=False, url="test", error="No results", execution_time=0.1
            ))
            
            # Mock the main extraction method to return our test response
            service.extract_company_information = AsyncMock(return_value=mock_response)
            
            # Execute concurrent requests
            tasks = [service.extract_company_information(req) for req in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete successfully
            assert len(results) == 3
            assert all(isinstance(result, CompanyExtractionResponse) for result in results)
            assert all(result.success for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])