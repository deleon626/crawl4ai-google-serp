"""Comprehensive tests for CompanyExtractionService."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.company_service import CompanyExtractionService
from app.models.company import (
    CompanyInformationRequest, ExtractionMode, CompanyInformation,
    CompanyBasicInfo, CompanyContact, CompanySocial, SocialPlatformType
)
from app.models.serp import SearchResponse, SearchResult, PaginationMetadata
from app.models.crawl import CrawlResponse, CrawlResult
from app.utils.exceptions import BrightDataError


class TestCompanyExtractionService:
    """Test suite for CompanyExtractionService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return CompanyExtractionService()
    
    @pytest.fixture
    def sample_request(self):
        """Create sample company information request."""
        return CompanyInformationRequest(
            company_name="OpenAI",
            domain="openai.com",
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            country="US",
            language="en",
            max_pages_to_crawl=3,
            timeout_seconds=30
        )
    
    @pytest.fixture
    def mock_search_response(self):
        """Create mock SERP search response."""
        return SearchResponse(
            query="OpenAI company information",
            results_count=3,
            organic_results=[
                SearchResult(
                    rank=1,
                    title="OpenAI - About Us",
                    url="https://openai.com/about",
                    description="OpenAI is an AI research and deployment company."
                ),
                SearchResult(
                    rank=2,
                    title="OpenAI - Contact Information",
                    url="https://openai.com/contact",
                    description="Contact OpenAI for inquiries and support."
                ),
                SearchResult(
                    rank=3,
                    title="OpenAI | LinkedIn",
                    url="https://linkedin.com/company/openai",
                    description="OpenAI company page on LinkedIn."
                )
            ],
            search_metadata={"total_results": 150, "time_taken": 0.5}
        )
    
    @pytest.fixture
    def mock_crawl_response(self):
        """Create mock crawl response."""
        return CrawlResponse(
            success=True,
            url="https://openai.com/about",
            result=CrawlResult(
                url="https://openai.com/about",
                title="OpenAI - About Us",
                markdown="# OpenAI\n\nOpenAI is an AI research and deployment company...",
                cleaned_html="<h1>OpenAI</h1><p>OpenAI is an AI research and deployment company...</p>",
                metadata={"word_count": 500},
                media=[],
                links=[]
            ),
            error=None,
            execution_time=2.3
        )
    
    @pytest.fixture
    def sample_company_info(self):
        """Create sample company information."""
        return CompanyInformation(
            basic_info=CompanyBasicInfo(
                name="OpenAI",
                domain="openai.com",
                website="https://openai.com",
                description="AI research and deployment company",
                industry="Artificial Intelligence",
                founded_year=2015,
                headquarters="San Francisco, CA, USA"
            ),
            contact=CompanyContact(
                email="contact@openai.com",
                address="3180 18th St, San Francisco, CA 94110"
            ),
            social_media=[
                CompanySocial(
                    platform=SocialPlatformType.LINKEDIN,
                    url="https://linkedin.com/company/openai",
                    username="openai"
                )
            ],
            confidence_score=0.85,
            data_quality_score=0.80,
            completeness_score=0.75
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization and context manager."""
        assert service.serp_service is None
        assert service.crawl_service is None
        assert service.company_parser is not None
        
        # Test context manager
        async with service:
            assert service.serp_service is not None
            assert service.crawl_service is not None
    
    @pytest.mark.asyncio
    async def test_extract_company_information_success(
        self, service, sample_request, mock_search_response, 
        mock_crawl_response, sample_company_info
    ):
        """Test successful company information extraction."""
        # Mock services
        with patch.object(service, 'serp_service') as mock_serp, \
             patch.object(service, 'crawl_service') as mock_crawl:
            
            # Mock service initialization
            service.serp_service = AsyncMock()
            service.crawl_service = AsyncMock()
            
            # Mock SERP search
            service.serp_service.search = AsyncMock(return_value=mock_search_response)
            
            # Mock crawling
            service.crawl_service.crawl = AsyncMock(return_value=mock_crawl_response)
            
            # Mock parser
            with patch.object(service.company_parser, 'extract_company_information') as mock_parse:
                mock_parse.return_value = sample_company_info
                
                # Execute extraction
                async with service:
                    response = await service.extract_company_information(sample_request)
                
                # Verify response
                assert response.success is True
                assert response.company_name == "OpenAI"
                assert response.company_information is not None
                assert response.company_information.basic_info.name == "OpenAI"
                assert len(response.errors) == 0
                assert response.extraction_metadata.pages_crawled >= 1
    
    @pytest.mark.asyncio
    async def test_extract_company_information_search_failure(self, service, sample_request):
        """Test extraction with search failure."""
        with patch.object(service, 'serp_service') as mock_serp, \
             patch.object(service, 'crawl_service') as mock_crawl:
            
            service.serp_service = AsyncMock()
            service.crawl_service = AsyncMock()
            
            # Mock search failure
            service.serp_service.search = AsyncMock(side_effect=BrightDataError("API Error"))
            
            async with service:
                response = await service.extract_company_information(sample_request)
            
            # Should still complete but with limited success
            assert response.success is False
            assert len(response.errors) > 0
            assert "SearchError" in [error.error_type for error in response.errors]
    
    @pytest.mark.asyncio
    async def test_extract_company_information_crawl_failure(
        self, service, sample_request, mock_search_response
    ):
        """Test extraction with crawl failure."""
        with patch.object(service, 'serp_service') as mock_serp, \
             patch.object(service, 'crawl_service') as mock_crawl:
            
            service.serp_service = AsyncMock()
            service.crawl_service = AsyncMock()
            
            # Mock successful search
            service.serp_service.search = AsyncMock(return_value=mock_search_response)
            
            # Mock crawl failure
            failed_crawl = CrawlResponse(
                success=False,
                url="https://openai.com/about",
                result=None,
                error="Timeout error",
                execution_time=30.0
            )
            service.crawl_service.crawl = AsyncMock(return_value=failed_crawl)
            
            async with service:
                response = await service.extract_company_information(sample_request)
            
            assert response.success is False
            assert len(response.errors) > 0
            assert "CrawlError" in [error.error_type for error in response.errors]
    
    def test_generate_search_queries(self, service):
        """Test search query generation."""
        request = CompanyInformationRequest(
            company_name="OpenAI",
            domain="openai.com",
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            include_social_media=True,
            include_key_personnel=True
        )
        
        queries = service._generate_search_queries(request)
        
        assert len(queries) > 5
        assert '"OpenAI" site:openai.com' in queries
        assert '"OpenAI" contact information' in queries
        assert '"OpenAI" linkedin' in queries
        assert '"OpenAI" CEO founder' in queries
    
    def test_generate_search_queries_contact_focused(self, service):
        """Test search query generation for contact-focused mode."""
        request = CompanyInformationRequest(
            company_name="TechCorp",
            extraction_mode=ExtractionMode.CONTACT_FOCUSED,
            include_social_media=False,
            include_key_personnel=False
        )
        
        queries = service._generate_search_queries(request)
        
        contact_queries = [q for q in queries if 'contact' in q.lower() or 'address' in q.lower()]
        assert len(contact_queries) > 0
        
        # Should not include social media queries
        social_queries = [q for q in queries if 'linkedin' in q.lower() or 'twitter' in q.lower()]
        assert len(social_queries) == 0
    
    def test_score_url_priority_official_domain(self, service):
        """Test URL priority scoring for official domain."""
        request = CompanyInformationRequest(
            company_name="OpenAI",
            domain="openai.com"
        )
        
        # Official domain should get high score
        score = service._score_url_priority(
            "https://openai.com/about",
            "OpenAI - About Us",
            "Learn about OpenAI company",
            request
        )
        assert score > 0.5
        
        # Third-party domain should get lower score
        score2 = service._score_url_priority(
            "https://example.com/openai-review",
            "OpenAI Review",
            "Review of OpenAI company",
            request
        )
        assert score2 < score
    
    def test_score_url_priority_high_value_paths(self, service):
        """Test URL priority scoring for high-value paths."""
        request = CompanyInformationRequest(
            company_name="TechCorp",
            domain="techcorp.com"
        )
        
        # About page should score higher than generic page
        about_score = service._score_url_priority(
            "https://techcorp.com/about",
            "TechCorp - About Us",
            "About TechCorp company",
            request
        )
        
        generic_score = service._score_url_priority(
            "https://techcorp.com/products",
            "TechCorp Products",
            "TechCorp product listings",
            request
        )
        
        assert about_score > generic_score
    
    def test_score_url_priority_contact_focused_mode(self, service):
        """Test URL priority scoring for contact-focused mode."""
        request = CompanyInformationRequest(
            company_name="TechCorp",
            extraction_mode=ExtractionMode.CONTACT_FOCUSED
        )
        
        # Contact page should score higher in contact-focused mode
        contact_score = service._score_url_priority(
            "https://techcorp.com/contact",
            "TechCorp - Contact Us",
            "Contact information for TechCorp",
            request
        )
        
        about_score = service._score_url_priority(
            "https://techcorp.com/about",
            "TechCorp - About",
            "About TechCorp company",
            request
        )
        
        # Contact should have additional scoring boost
        assert contact_score >= about_score
    
    def test_score_url_priority_linkedin_domain(self, service):
        """Test URL priority scoring for LinkedIn domain."""
        request = CompanyInformationRequest(
            company_name="OpenAI"
        )
        
        linkedin_score = service._score_url_priority(
            "https://linkedin.com/company/openai",
            "OpenAI | LinkedIn",
            "OpenAI company page on LinkedIn",
            request
        )
        
        # LinkedIn should get a decent score as high-value domain
        assert linkedin_score > 0.2
    
    def test_score_url_priority_irrelevant_domains(self, service):
        """Test URL priority scoring penalizes irrelevant domains."""
        request = CompanyInformationRequest(
            company_name="OpenAI"
        )
        
        # Social media domains should get penalized
        facebook_score = service._score_url_priority(
            "https://facebook.com/openai",
            "OpenAI on Facebook",
            "OpenAI Facebook page",
            request
        )
        
        # Official domain should score higher
        official_score = service._score_url_priority(
            "https://openai.com/about",
            "OpenAI - About",
            "About OpenAI",
            request
        )
        
        assert official_score > facebook_score
    
    def test_aggregate_company_information_single_source(self, service, sample_company_info):
        """Test aggregation with single source."""
        parsed_infos = [(sample_company_info, "https://openai.com", {})]
        
        result = service._aggregate_company_information(parsed_infos)
        
        assert result == sample_company_info
        assert result.basic_info.name == "OpenAI"
    
    def test_aggregate_company_information_multiple_sources(self, service):
        """Test aggregation with multiple sources."""
        # Create first source with basic info
        info1 = CompanyInformation(
            basic_info=CompanyBasicInfo(
                name="OpenAI",
                domain="openai.com",
                description="AI research company"
            ),
            confidence_score=0.8
        )
        
        # Create second source with contact info
        info2 = CompanyInformation(
            basic_info=CompanyBasicInfo(
                name="OpenAI",
                headquarters="San Francisco, CA"
            ),
            contact=CompanyContact(
                email="contact@openai.com",
                phone="+1-415-555-0123"
            ),
            confidence_score=0.7
        )
        
        # Create third source with social media
        info3 = CompanyInformation(
            basic_info=CompanyBasicInfo(name="OpenAI"),
            social_media=[
                CompanySocial(
                    platform=SocialPlatformType.LINKEDIN,
                    url="https://linkedin.com/company/openai",
                    username="openai"
                )
            ],
            confidence_score=0.6
        )
        
        parsed_infos = [
            (info1, "https://openai.com", {}),
            (info2, "https://openai.com/contact", {}),
            (info3, "https://linkedin.com/company/openai", {})
        ]
        
        result = service._aggregate_company_information(parsed_infos)
        
        # Should have combined information
        assert result.basic_info.name == "OpenAI"
        assert result.basic_info.description == "AI research company"
        assert result.basic_info.headquarters == "San Francisco, CA"
        assert result.contact is not None
        assert result.contact.email == "contact@openai.com"
        assert len(result.social_media) == 1
        assert result.social_media[0].platform == SocialPlatformType.LINKEDIN
        
        # Confidence should be boosted for multiple sources
        assert result.confidence_score > 0.8
    
    def test_aggregate_company_information_deduplicate_social(self, service):
        """Test social media deduplication during aggregation."""
        # Two sources with same LinkedIn profile
        linkedin_social = CompanySocial(
            platform=SocialPlatformType.LINKEDIN,
            url="https://linkedin.com/company/openai",
            username="openai"
        )
        
        info1 = CompanyInformation(
            basic_info=CompanyBasicInfo(name="OpenAI"),
            social_media=[linkedin_social],
            confidence_score=0.8
        )
        
        info2 = CompanyInformation(
            basic_info=CompanyBasicInfo(name="OpenAI"),
            social_media=[linkedin_social],  # Same profile
            confidence_score=0.7
        )
        
        parsed_infos = [
            (info1, "https://openai.com", {}),
            (info2, "https://linkedin.com/company/openai", {})
        ]
        
        result = service._aggregate_company_information(parsed_infos)
        
        # Should have only one LinkedIn profile
        assert len(result.social_media) == 1
        assert result.social_media[0].platform == SocialPlatformType.LINKEDIN
    
    @pytest.mark.asyncio
    async def test_get_service_status(self, service):
        """Test service status reporting."""
        status = await service.get_service_status()
        
        assert "status" in status
        assert "service_version" in status
        assert status["serp_service_initialized"] is False
        assert status["crawl_service_initialized"] is False
        assert status["parser_initialized"] is True
    
    @pytest.mark.asyncio
    async def test_get_service_status_with_services(self, service):
        """Test service status with initialized services."""
        async with service:
            # Mock service status
            service.serp_service.get_service_status = AsyncMock(
                return_value={"status": "operational"}
            )
            
            status = await service.get_service_status()
            
            assert status["serp_service_initialized"] is True
            assert status["crawl_service_initialized"] is True
            assert status["serp_service_status"] == "operational"
    
    @pytest.mark.asyncio 
    async def test_context_manager_exception_handling(self, service):
        """Test context manager handles exceptions properly."""
        try:
            async with service:
                # Mock services for context
                service.serp_service = AsyncMock()
                service.crawl_service = AsyncMock()
                
                # Simulate exception
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Services should still be cleaned up
        assert service.serp_service is not None  # Still exists but should be closed
    
    def test_empty_aggregation_raises_error(self, service):
        """Test aggregation with empty list raises error."""
        with pytest.raises(ValueError):
            service._aggregate_company_information([])
    
    @pytest.mark.asyncio
    async def test_extract_with_minimal_request(self, service):
        """Test extraction with minimal request parameters."""
        minimal_request = CompanyInformationRequest(
            company_name="TestCorp",
            extraction_mode=ExtractionMode.BASIC,
            max_pages_to_crawl=1,
            timeout_seconds=10
        )
        
        # Mock empty responses
        with patch.object(service, 'serp_service') as mock_serp, \
             patch.object(service, 'crawl_service') as mock_crawl:
            
            service.serp_service = AsyncMock()
            service.crawl_service = AsyncMock()
            
            # Mock empty search response
            empty_response = SearchResponse(
                query="TestCorp company information",
                results_count=0,
                organic_results=[],
                search_metadata={"total_results": 0, "time_taken": 0.1}
            )
            service.serp_service.search = AsyncMock(return_value=empty_response)
            
            async with service:
                response = await service.extract_company_information(minimal_request)
            
            assert response.company_name == "TestCorp"
            assert response.success is False
            assert response.extraction_metadata.pages_attempted == 0
            assert response.extraction_metadata.extraction_mode_used == ExtractionMode.BASIC


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])