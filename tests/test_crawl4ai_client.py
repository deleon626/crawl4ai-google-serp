"""Tests for Crawl4ai client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.clients.crawl4ai_client import Crawl4aiClient


class TestCrawl4aiClient:
    """Test cases for Crawl4ai client."""
    
    @pytest.fixture
    def client(self):
        """Create Crawl4ai client fixture."""
        return Crawl4aiClient()
    
    @pytest.fixture
    def mock_crawler_result(self):
        """Mock crawler result fixture."""
        result = MagicMock()
        result.success = True
        result.url = "https://example.com"
        result.title = "Example Title"
        result.markdown = "Example content in markdown"
        result.cleaned_html = "<p>Example content</p>"
        result.images = ["https://example.com/image.jpg"]
        result.videos = []
        result.internal_links = ["https://example.com/about"]
        result.external_links = ["https://external.com"]
        result.status_code = 200
        result.response_headers = {"content-type": "text/html"}
        return result
    
    @pytest.mark.asyncio
    async def test_crawl_url_success(self, client, mock_crawler_result):
        """Test successful URL crawling."""
        with patch('app.clients.crawl4ai_client.AsyncWebCrawler') as mock_crawler_class:
            # Setup mock crawler
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler.arun = AsyncMock(return_value=mock_crawler_result)
            
            # Execute crawl
            result = await client.crawl_url("https://example.com")
            
            # Assertions
            assert result["success"] is True
            assert result["url"] == "https://example.com"
            assert result["result"]["title"] == "Example Title"
            assert result["result"]["markdown"] == "Example content in markdown"
            assert result["result"]["media"]["images"] == ["https://example.com/image.jpg"]
            assert result["execution_time"] > 0
    
    @pytest.mark.asyncio
    async def test_crawl_url_failure(self, client):
        """Test URL crawling failure."""
        with patch('app.clients.crawl4ai_client.AsyncWebCrawler') as mock_crawler_class:
            # Setup mock crawler with failure
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            
            # Mock failed result
            failed_result = MagicMock()
            failed_result.success = False
            failed_result.error = "Connection timeout"
            mock_crawler.arun = AsyncMock(return_value=failed_result)
            
            # Execute crawl
            result = await client.crawl_url("https://invalid-url.com")
            
            # Assertions
            assert result["success"] is False
            assert "Connection timeout" in result["error"]
            assert result["result"] is None
    
    @pytest.mark.asyncio
    async def test_crawl_url_exception(self, client):
        """Test URL crawling with exception."""
        with patch('app.clients.crawl4ai_client.AsyncWebCrawler') as mock_crawler_class:
            # Setup mock crawler that raises exception
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler.arun = AsyncMock(side_effect=Exception("Network error"))
            
            # Execute crawl
            result = await client.crawl_url("https://example.com")
            
            # Assertions
            assert result["success"] is False
            assert "Network error" in result["error"]
            assert result["result"] is None
    
    def test_get_extraction_strategy(self, client):
        """Test extraction strategy selection."""
        # Test valid strategies
        strategy = client._get_extraction_strategy("NoExtractionStrategy")
        assert strategy is not None
        
        strategy = client._get_extraction_strategy("LLMExtractionStrategy") 
        assert strategy is not None
        
        # Test invalid strategy (should default to NoExtractionStrategy)
        strategy = client._get_extraction_strategy("InvalidStrategy")
        assert strategy is not None
    
    def test_get_chunking_strategy(self, client):
        """Test chunking strategy selection."""
        # Test valid strategies
        strategy = client._get_chunking_strategy("RegexChunking")
        assert strategy is not None
        
        strategy = client._get_chunking_strategy("IdentityChunking")
        assert strategy is not None
        
        # Test invalid strategy (should default to RegexChunking)
        strategy = client._get_chunking_strategy("InvalidStrategy")
        assert strategy is not None