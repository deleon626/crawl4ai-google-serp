"""Error handling integration tests for company extraction functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC

from app.services.company_service import CompanyExtractionService
from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, ExtractionMode,
    ExtractionError, ExtractionMetadata
)
from app.models.serp import SearchResponse, SearchResult
from app.models.crawl import CrawlResponse
from app.utils.exceptions import (
    BrightDataError, BrightDataRateLimitError, BrightDataTimeoutError,
    CompanyAnalysisError
)


class TestSearchErrorHandling:
    """Test error handling for search-related failures."""
    
    @pytest.fixture
    async def service(self):
        """Create service for testing."""
        service = CompanyExtractionService()
        async with service:
            yield service
    
    @pytest.fixture
    def basic_request(self):
        """Basic extraction request."""
        return CompanyInformationRequest(
            company_name="ErrorTestCorp",
            max_pages_to_crawl=3,
            timeout_seconds=30
        )
    
    @pytest.mark.asyncio
    async def test_search_api_unavailable(self, service, basic_request):
        """Test handling when search API is completely unavailable."""
        # Mock complete API failure
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataError("Service unavailable")
        )
        
        response = await service.extract_company_information(basic_request)
        
        # Should fail gracefully
        assert response.success is False
        assert len(response.errors) > 0
        
        # Should have search-related error
        search_errors = [e for e in response.errors if "search" in e.error_type.lower()]
        assert len(search_errors) > 0
        
        # Should have appropriate error message
        error_messages = [e.error_message for e in response.errors]
        assert any("service unavailable" in msg.lower() for msg in error_messages)
        
        # Metadata should reflect failure
        assert response.extraction_metadata.pages_attempted == 0
        assert response.extraction_metadata.pages_crawled == 0
    
    @pytest.mark.asyncio
    async def test_search_rate_limit_handling(self, service, basic_request):
        """Test handling of search API rate limits."""
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataRateLimitError("Rate limit exceeded")
        )
        
        response = await service.extract_company_information(basic_request)
        
        assert response.success is False
        assert len(response.errors) > 0
        
        # Should have rate limit error
        rate_limit_errors = [e for e in response.errors 
                           if "rate" in e.error_type.lower() or "limit" in e.error_type.lower()]
        assert len(rate_limit_errors) > 0
        
        # Should suggest retry in warnings
        assert len(response.warnings) > 0
        warning_text = " ".join(response.warnings).lower()
        assert "retry" in warning_text or "later" in warning_text
    
    @pytest.mark.asyncio
    async def test_search_timeout_handling(self, service, basic_request):
        """Test handling of search timeouts."""
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataTimeoutError("Request timeout after 30s")
        )
        
        response = await service.extract_company_information(basic_request)
        
        assert response.success is False
        assert len(response.errors) > 0
        
        # Should have timeout error
        timeout_errors = [e for e in response.errors if "timeout" in e.error_type.lower()]
        assert len(timeout_errors) > 0
        
        # Should complete in reasonable time
        assert response.processing_time < 60  # Should not wait for full timeout
    
    @pytest.mark.asyncio
    async def test_search_authentication_failure(self, service, basic_request):
        """Test handling of authentication failures."""
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataError("Authentication failed")
        )
        
        response = await service.extract_company_information(basic_request)
        
        assert response.success is False
        assert len(response.errors) > 0
        
        # Should have authentication error
        auth_errors = [e for e in response.errors 
                      if "auth" in e.error_type.lower() or "authentication" in e.error_message.lower()]
        assert len(auth_errors) > 0
    
    @pytest.mark.asyncio
    async def test_search_empty_results_handling(self, service, basic_request):
        """Test handling when search returns no results."""
        empty_response = SearchResponse(
            query="NoResultsCorp company information",
            results_count=0,
            organic_results=[],
            search_metadata={"total_results": 0, "time_taken": 0.1}
        )
        
        service.serp_service.search = AsyncMock(return_value=empty_response)
        
        response = await service.extract_company_information(basic_request)
        
        # Should complete but with limited success
        assert response.success is False or len(response.warnings) > 0
        assert response.extraction_metadata.pages_attempted == 0
        
        # Should have appropriate warnings about no results
        warning_text = " ".join(response.warnings).lower()
        assert "no results" in warning_text or "not found" in warning_text
    
    @pytest.mark.asyncio
    async def test_search_malformed_results(self, service, basic_request):
        """Test handling of malformed search results."""
        # Create search response with problematic URLs
        malformed_response = SearchResponse(
            query="MalformedCorp",
            results_count=3,
            organic_results=[
                SearchResult(rank=1, title="Valid", url="https://valid.com", description="Valid"),
                SearchResult(rank=2, title="Invalid", url="invalid-url", description="Invalid URL"),
                SearchResult(rank=3, title="Empty", url="", description="Empty URL"),
            ]
        )
        
        service.serp_service.search = AsyncMock(return_value=malformed_response)
        service.crawl_service.crawl = AsyncMock(
            side_effect=Exception("Invalid URL format")
        )
        
        response = await service.extract_company_information(basic_request)
        
        # Should handle malformed URLs gracefully
        assert response.extraction_metadata.pages_attempted >= 1
        
        # Should have appropriate errors for invalid URLs
        url_errors = [e for e in response.errors if "url" in e.error_message.lower()]
        assert len(url_errors) > 0


class TestCrawlErrorHandling:
    """Test error handling for crawl-related failures."""
    
    @pytest.fixture
    async def service(self):
        """Create service for testing.""" 
        service = CompanyExtractionService()
        async with service:
            yield service
    
    @pytest.fixture
    def request_with_urls(self):
        """Request that will generate URLs to crawl."""
        return CompanyInformationRequest(
            company_name="CrawlTestCorp",
            domain="crawltest.com",
            max_pages_to_crawl=5,
            timeout_seconds=30
        )
    
    @pytest.fixture
    def mock_search_response(self):
        """Mock search response with multiple URLs."""
        return SearchResponse(
            query="CrawlTestCorp",
            results_count=5,
            organic_results=[
                SearchResult(rank=1, title="Home", url="https://crawltest.com", description="Home page"),
                SearchResult(rank=2, title="About", url="https://crawltest.com/about", description="About page"),
                SearchResult(rank=3, title="Contact", url="https://crawltest.com/contact", description="Contact page"),
                SearchResult(rank=4, title="News", url="https://crawltest.com/news", description="News page"),
                SearchResult(rank=5, title="Careers", url="https://crawltest.com/careers", description="Careers page"),
            ]
        )
    
    @pytest.mark.asyncio
    async def test_crawl_service_unavailable(self, service, request_with_urls, mock_search_response):
        """Test handling when crawl service is completely unavailable."""
        service.serp_service.search = AsyncMock(return_value=mock_search_response)
        service.crawl_service.crawl = AsyncMock(
            side_effect=Exception("Crawl service unavailable")
        )
        
        response = await service.extract_company_information(request_with_urls)
        
        # Should fail but complete processing
        assert len(response.errors) > 0
        
        # Should have crawl-related errors
        crawl_errors = [e for e in response.errors if "crawl" in e.error_type.lower()]
        assert len(crawl_errors) > 0
        
        # Should attempt multiple URLs despite failures
        assert response.extraction_metadata.pages_attempted >= 3
        assert response.extraction_metadata.pages_crawled == 0
    
    @pytest.mark.asyncio
    async def test_mixed_crawl_success_failure(self, service, request_with_urls, mock_search_response):
        """Test handling of mixed crawl success and failures."""
        service.serp_service.search = AsyncMock(return_value=mock_search_response)
        
        # Create mixed responses: some succeed, some fail
        responses = [
            CrawlResponse(success=True, url="https://crawltest.com", result=MagicMock(), execution_time=1.0),
            CrawlResponse(success=False, url="https://crawltest.com/about", error="403 Forbidden", execution_time=2.0),
            CrawlResponse(success=True, url="https://crawltest.com/contact", result=MagicMock(), execution_time=1.5),
            CrawlResponse(success=False, url="https://crawltest.com/news", error="Timeout", execution_time=30.0),
            CrawlResponse(success=False, url="https://crawltest.com/careers", error="404 Not Found", execution_time=1.0),
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=responses)
        
        response = await service.extract_company_information(request_with_urls)
        
        # Should have partial success
        assert response.extraction_metadata.pages_attempted == 5
        assert response.extraction_metadata.pages_crawled == 2  # 2 successful
        
        # Should have errors for failed crawls
        assert len(response.errors) >= 3  # 3 failed crawls
        
        # Should categorize different error types
        error_types = [e.error_type for e in response.errors]
        assert any("403" in et or "Forbidden" in et for et in error_types)
        assert any("404" in et or "NotFound" in et for et in error_types)
        assert any("Timeout" in et for et in error_types)
    
    @pytest.mark.asyncio
    async def test_crawl_timeout_handling(self, service, request_with_urls, mock_search_response):
        """Test handling of crawl timeouts."""
        service.serp_service.search = AsyncMock(return_value=mock_search_response)
        
        # Mock crawl with timeout errors
        async def mock_crawl_with_timeout(request):
            await asyncio.sleep(0.1)  # Simulate processing
            if "about" in request.url:
                return CrawlResponse(
                    success=False,
                    url=request.url,
                    error="Timeout after 30 seconds",
                    execution_time=30.0
                )
            else:
                return CrawlResponse(
                    success=True,
                    url=request.url,
                    result=MagicMock(),
                    execution_time=2.0
                )
        
        service.crawl_service.crawl = mock_crawl_with_timeout
        
        response = await service.extract_company_information(request_with_urls)
        
        # Should handle timeouts gracefully
        timeout_errors = [e for e in response.errors if "timeout" in e.error_message.lower()]
        assert len(timeout_errors) >= 1
        
        # Should continue processing other URLs despite timeouts
        assert response.extraction_metadata.pages_crawled >= 1
    
    @pytest.mark.asyncio
    async def test_crawl_memory_exhaustion(self, service, request_with_urls, mock_search_response):
        """Test handling of memory-related crawl failures."""
        service.serp_service.search = AsyncMock(return_value=mock_search_response)
        service.crawl_service.crawl = AsyncMock(
            side_effect=MemoryError("Out of memory during crawl")
        )
        
        response = await service.extract_company_information(request_with_urls)
        
        # Should handle memory errors gracefully
        assert len(response.errors) > 0
        
        # Should have memory-related errors
        memory_errors = [e for e in response.errors if "memory" in e.error_message.lower()]
        assert len(memory_errors) > 0
        
        # Should suggest reducing crawl scope in warnings
        warning_text = " ".join(response.warnings).lower()
        assert any(keyword in warning_text for keyword in ["reduce", "scope", "pages", "limit"])
    
    @pytest.mark.asyncio
    async def test_crawl_network_errors(self, service, request_with_urls, mock_search_response):
        """Test handling of various network-related crawl errors."""
        service.serp_service.search = AsyncMock(return_value=mock_search_response)
        
        network_errors = [
            ConnectionError("Connection refused"),
            ConnectionError("DNS resolution failed"),
            TimeoutError("Network timeout"),
            Exception("SSL certificate error"),
            Exception("Connection reset by peer"),
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=network_errors)
        
        response = await service.extract_company_information(request_with_urls)
        
        # Should handle all network errors gracefully
        assert len(response.errors) >= len(network_errors)
        
        # Should categorize network errors appropriately
        network_error_count = len([e for e in response.errors 
                                  if any(keyword in e.error_message.lower() 
                                        for keyword in ["connection", "network", "timeout", "ssl", "dns"])])
        assert network_error_count >= 3


class TestParsingErrorHandling:
    """Test error handling for parsing-related failures."""
    
    @pytest.fixture
    async def service(self):
        """Create service for testing."""
        service = CompanyExtractionService()
        async with service:
            yield service
    
    @pytest.fixture
    def request_with_domain(self):
        """Request with domain for parsing tests."""
        return CompanyInformationRequest(
            company_name="ParseTestCorp",
            domain="parsetest.com"
        )
    
    @pytest.mark.asyncio
    async def test_malformed_html_handling(self, service, request_with_domain):
        """Test handling of malformed HTML content."""
        # Mock search and crawl to return malformed HTML
        mock_search = SearchResponse(
            query="test", results_count=1,
            organic_results=[SearchResult(rank=1, title="Test", url="https://parsetest.com", description="Test")]
        )
        
        malformed_html = """
        <html>
            <head>
                <title>ParseTestCorp
            <body>
                <h1>Welcome to ParseTestCorp
                <p>Unclosed tags and malformed structure
                <div><span>Nested without closing
                <script>alert('potentially dangerous content');</script>
        """
        
        mock_crawl = CrawlResponse(
            success=True,
            url="https://parsetest.com",
            result=MagicMock(
                url="https://parsetest.com",
                title="ParseTestCorp",
                cleaned_html=malformed_html,
                markdown="# ParseTestCorp\nMalformed content",
                metadata={}
            ),
            execution_time=2.0
        )
        
        service.serp_service.search = AsyncMock(return_value=mock_search)
        service.crawl_service.crawl = AsyncMock(return_value=mock_crawl)
        
        response = await service.extract_company_information(request_with_domain)
        
        # Should handle malformed HTML gracefully
        assert response.company_information is not None
        assert response.company_information.basic_info.name is not None
        
        # May have parsing warnings
        if response.warnings:
            warning_text = " ".join(response.warnings).lower()
            assert any(keyword in warning_text for keyword in ["parsing", "html", "format"])
    
    @pytest.mark.asyncio
    async def test_empty_content_handling(self, service, request_with_domain):
        """Test handling of empty or minimal content."""
        mock_search = SearchResponse(
            query="test", results_count=1,
            organic_results=[SearchResult(rank=1, title="Test", url="https://parsetest.com", description="Test")]
        )
        
        # Empty content response
        empty_crawl = CrawlResponse(
            success=True,
            url="https://parsetest.com",
            result=MagicMock(
                url="https://parsetest.com",
                title="",
                cleaned_html="<html></html>",
                markdown="",
                metadata={"word_count": 0}
            ),
            execution_time=1.0
        )
        
        service.serp_service.search = AsyncMock(return_value=mock_search)
        service.crawl_service.crawl = AsyncMock(return_value=empty_crawl)
        
        response = await service.extract_company_information(request_with_domain)
        
        # Should handle empty content gracefully
        assert response.company_information is not None
        
        # Should have low confidence scores
        assert response.company_information.confidence_score <= 0.3
        assert response.company_information.completeness_score <= 0.2
        
        # Should have warnings about limited content
        assert len(response.warnings) > 0
        warning_text = " ".join(response.warnings).lower()
        assert any(keyword in warning_text for keyword in ["limited", "empty", "minimal", "content"])
    
    @pytest.mark.asyncio
    async def test_parser_exception_handling(self, service, request_with_domain):
        """Test handling when parser itself throws exceptions."""
        mock_search = SearchResponse(
            query="test", results_count=1,
            organic_results=[SearchResult(rank=1, title="Test", url="https://parsetest.com", description="Test")]
        )
        
        mock_crawl = CrawlResponse(
            success=True,
            url="https://parsetest.com",
            result=MagicMock(
                url="https://parsetest.com",
                title="Test",
                cleaned_html="<html><body>Test content</body></html>",
                markdown="# Test\nTest content"
            ),
            execution_time=1.0
        )
        
        service.serp_service.search = AsyncMock(return_value=mock_search)
        service.crawl_service.crawl = AsyncMock(return_value=mock_crawl)
        
        # Mock parser to throw exception
        with patch.object(service.company_parser, 'extract_company_information') as mock_parse:
            mock_parse.side_effect = Exception("Parser internal error")
            
            response = await service.extract_company_information(request_with_domain)
            
            # Should handle parser exception gracefully
            assert len(response.errors) > 0
            
            # Should have parsing error
            parse_errors = [e for e in response.errors if "parse" in e.error_type.lower()]
            assert len(parse_errors) > 0


class TestSystemLevelErrorHandling:
    """Test system-level error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_service_initialization_failure(self):
        """Test handling of service initialization failures."""
        with patch('app.services.serp_service.SERPService.__aenter__') as mock_serp_init:
            mock_serp_init.side_effect = Exception("Service initialization failed")
            
            service = CompanyExtractionService()
            
            with pytest.raises(Exception, match="Service initialization failed"):
                async with service:
                    pass
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling with concurrent operations."""
        service = CompanyExtractionService()
        
        # Create requests that will fail in different ways
        requests = [
            CompanyInformationRequest(company_name="TimeoutCorp"),
            CompanyInformationRequest(company_name="NetworkCorp"), 
            CompanyInformationRequest(company_name="ParseCorp"),
        ]
        
        async with service:
            # Mock different types of failures
            service.serp_service.search = AsyncMock(
                side_effect=[
                    BrightDataTimeoutError("Timeout"),
                    ConnectionError("Network error"),
                    BrightDataError("Parse error")
                ]
            )
            
            # Execute concurrent requests
            tasks = [service.extract_company_information(req) for req in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete (not raise exceptions)
            assert len(results) == 3
            assert all(isinstance(result, CompanyExtractionResponse) for result in results)
            
            # All should have errors recorded
            assert all(len(result.errors) > 0 for result in results)
            assert all(not result.success for result in results)
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_handling(self):
        """Test handling of resource exhaustion scenarios."""
        service = CompanyExtractionService()
        
        request = CompanyInformationRequest(
            company_name="ResourceCorp",
            max_pages_to_crawl=20,  # High number to potentially exhaust resources
            timeout_seconds=120
        )
        
        async with service:
            # Mock resource exhaustion
            service.serp_service.search = AsyncMock(
                side_effect=MemoryError("Insufficient memory")
            )
            
            response = await service.extract_company_information(request)
            
            # Should handle resource exhaustion gracefully
            assert response is not None
            assert len(response.errors) > 0
            
            # Should suggest resource optimization
            if response.warnings:
                warning_text = " ".join(response.warnings).lower()
                assert any(keyword in warning_text 
                          for keyword in ["reduce", "limit", "memory", "resources"])
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures."""
        service = CompanyExtractionService()
        
        request = CompanyInformationRequest(company_name="CascadeCorp")
        
        # Track failure count
        failure_count = 0
        
        async def failing_search(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # Fail first few attempts
                raise BrightDataError(f"Failure {failure_count}")
            # Eventually succeed to test recovery
            return SearchResponse(query="test", results_count=0, organic_results=[])
        
        async with service:
            service.serp_service.search = failing_search
            
            response = await service.extract_company_information(request)
            
            # Should eventually succeed or fail gracefully without cascading
            assert response is not None
            assert response.processing_time < 60  # Should not hang indefinitely
            
            # Should record failures but continue processing
            if response.success:
                assert failure_count > 1  # Should have retried
            else:
                assert len(response.errors) > 0


class TestErrorReporting:
    """Test error reporting and diagnostic information."""
    
    @pytest.fixture
    async def service(self):
        """Create service for testing."""
        service = CompanyExtractionService()
        async with service:
            yield service
    
    @pytest.mark.asyncio
    async def test_error_context_preservation(self, service):
        """Test that error context is preserved for debugging."""
        request = CompanyInformationRequest(company_name="ContextCorp")
        
        # Mock specific error with context
        service.serp_service.search = AsyncMock(
            side_effect=BrightDataError("API key invalid for endpoint /search")
        )
        
        response = await service.extract_company_information(request)
        
        # Should preserve error context
        assert len(response.errors) > 0
        error = response.errors[0]
        
        assert error.error_type is not None
        assert error.error_message is not None
        assert isinstance(error.timestamp, datetime)
        
        # Should include contextual information
        assert "API key" in error.error_message or "search" in error.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_error_categorization(self, service):
        """Test that errors are properly categorized."""
        request = CompanyInformationRequest(company_name="CategoryCorp")
        
        # Mock different error types
        service.serp_service.search = AsyncMock(return_value=SearchResponse(
            query="test", results_count=1,
            organic_results=[SearchResult(rank=1, title="Test", url="https://test.com", description="Test")]
        ))
        
        errors = [
            BrightDataTimeoutError("Request timeout"),
            BrightDataRateLimitError("Rate limit exceeded"),
            ConnectionError("Network connection failed"),
            ValueError("Invalid parameter"),
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=errors)
        
        response = await service.extract_company_information(request)
        
        # Should categorize different error types
        error_types = [e.error_type for e in response.errors]
        
        # Should have distinct error types
        assert len(set(error_types)) >= 2  # At least 2 different error categories
        
        # Should categorize appropriately
        assert any("timeout" in et.lower() for et in error_types)
        assert any("rate" in et.lower() or "limit" in et.lower() for et in error_types)
    
    @pytest.mark.asyncio
    async def test_diagnostic_information_collection(self, service):
        """Test collection of diagnostic information."""
        request = CompanyInformationRequest(company_name="DiagnosticCorp")
        
        # Mock partial failures to generate diagnostic info
        service.serp_service.search = AsyncMock(return_value=SearchResponse(
            query="DiagnosticCorp", results_count=3,
            organic_results=[
                SearchResult(rank=1, title="Test1", url="https://test1.com", description="Test1"),
                SearchResult(rank=2, title="Test2", url="https://test2.com", description="Test2"),
                SearchResult(rank=3, title="Test3", url="https://test3.com", description="Test3"),
            ]
        ))
        
        # Mixed success/failure responses
        responses = [
            CrawlResponse(success=True, url="https://test1.com", result=MagicMock(), execution_time=1.0),
            CrawlResponse(success=False, url="https://test2.com", error="404 Not Found", execution_time=2.0),
            CrawlResponse(success=False, url="https://test3.com", error="Timeout", execution_time=30.0),
        ]
        
        service.crawl_service.crawl = AsyncMock(side_effect=responses)
        
        response = await service.extract_company_information(request)
        
        # Should collect comprehensive diagnostic information
        metadata = response.extraction_metadata
        
        # Should track processing metrics
        assert metadata.pages_attempted == 3
        assert metadata.pages_crawled == 1
        assert metadata.extraction_time > 0
        
        # Should track sources and queries
        assert len(metadata.search_queries_used) >= 1
        assert len(metadata.sources_found) >= 0  # May be 0 if extraction failed
        
        # Should provide error details
        assert len(response.errors) >= 2  # 2 failed crawls
        
        # Should provide processing time breakdown
        assert response.processing_time >= metadata.extraction_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])