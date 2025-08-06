"""Unit tests for Bright Data SERP API client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.clients.bright_data import (
    BrightDataClient, 
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)
from app.models.serp import SearchRequest, SearchResponse, SearchResult


class TestBrightDataClient:
    """Test cases for BrightDataClient."""

    @pytest.fixture
    def client(self):
        """Create a BrightDataClient instance for testing."""
        return BrightDataClient()

    @pytest.fixture
    def search_request(self):
        """Create a sample SearchRequest for testing."""
        return SearchRequest(
            query="test query",
            country="US",
            language="en",
            page=1
        )

    @pytest.fixture
    def mock_html_response(self):
        """Mock HTML response from Google search."""
        return """
        <html>
            <body>
                <div class="search-results">
                    <div class="result">
                        <h3>Test Result 1</h3>
                        <a href="https://example1.com">Example 1</a>
                        <span>Test description 1</span>
                    </div>
                    <div class="result">
                        <h3>Test Result 2</h3>
                        <a href="https://example2.com">Example 2</a>
                        <span>Test description 2</span>
                    </div>
                </div>
            </body>
        </html>
        """

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.api_url == "https://api.brightdata.com/request"
        assert client.zone == "serp_api1"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert "Bearer" in client.client.headers["Authorization"]

    def test_build_google_url(self, client, search_request):
        """Test Google URL building."""
        url = client._build_google_url(search_request)
        
        assert "https://www.google.com/search" in url
        assert "q=test%20query" in url
        assert "gl=us" in url
        assert "hl=en" in url
        assert "start=0" in url

    def test_build_google_url_pagination(self, client):
        """Test Google URL building with pagination."""
        search_request = SearchRequest(
            query="test",
            country="US",
            language="en",
            page=3
        )
        
        url = client._build_google_url(search_request)
        assert "start=20" in url

    @pytest.mark.asyncio
    async def test_search_success(self, client, search_request, mock_html_response):
        """Test successful search request."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = mock_html_response
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            # Mock the parser to return mock results
            with patch.object(client.parser, 'parse_html') as mock_parse:
                mock_search_response = SearchResponse(
                    query="test query",
                    results_count=1,
                    organic_results=[
                        SearchResult(
                            rank=1,
                            title="Test Result 1",
                            url="https://example1.com",
                            description="Test description 1"
                        )
                    ]
                )
                mock_parse.return_value = mock_search_response
                
                response = await client.search(search_request)
                
                assert isinstance(response, SearchResponse)
                assert response.query == "test query"
                assert response.results_count == 1
                assert len(response.organic_results) == 1
                assert response.organic_results[0].title == "Test Result 1"

    @pytest.mark.asyncio
    async def test_search_authentication_error(self, client, search_request):
        """Test search with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(BrightDataError, match="Authentication failed"):
                await client.search(search_request)

    @pytest.mark.asyncio
    async def test_search_rate_limit_error(self, client, search_request):
        """Test search with rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(BrightDataRateLimitError, match="Rate limit exceeded"):
                await client.search(search_request)

    @pytest.mark.asyncio
    async def test_search_bad_request_error(self, client, search_request):
        """Test search with bad request error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request parameters"
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(BrightDataError, match="Bad request"):
                await client.search(search_request)

    @pytest.mark.asyncio
    async def test_search_timeout_error(self, client, search_request):
        """Test search with timeout error."""
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(BrightDataTimeoutError, match="Request timeout"):
                await client.search(search_request)

    @pytest.mark.asyncio
    async def test_search_retry_logic(self, client, search_request, mock_html_response):
        """Test retry logic on temporary failures."""
        # First two calls fail, third succeeds
        mock_responses = [
            httpx.TimeoutException("Timeout"),
            httpx.RequestError("Connection error"),
            Mock(status_code=200, text=mock_html_response)
        ]
        
        call_count = 0
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            if call_count < 2:
                exception = mock_responses[call_count]
                call_count += 1
                raise exception
            else:
                call_count += 1
                return mock_responses[2]
        
        with patch.object(client.client, 'post', side_effect=mock_post):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up tests
                with patch.object(client.parser, 'parse_html') as mock_parse:
                    mock_parse.return_value = SearchResponse(
                        query="test query",
                        results_count=0,
                        organic_results=[]
                    )
                    response = await client.search(search_request)
                    assert isinstance(response, SearchResponse)

    @pytest.mark.asyncio
    async def test_search_max_retries_exceeded(self, client, search_request):
        """Test behavior when max retries are exceeded."""
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Persistent timeout")
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up tests
                with pytest.raises(BrightDataTimeoutError):
                    await client.search(search_request)

    def test_parser_integration(self, client):
        """Test that client properly uses the GoogleSERPParser."""
        assert hasattr(client, 'parser')
        assert client.parser is not None
        # The actual parsing logic is tested in the parser tests


    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with BrightDataClient() as client:
            assert isinstance(client, BrightDataClient)
            # Client should be properly initialized

    @pytest.mark.asyncio
    async def test_close_method(self, client):
        """Test client close method."""
        with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestSearchRequestValidation:
    """Test SearchRequest model validation."""

    def test_valid_search_request(self):
        """Test valid search request creation."""
        request = SearchRequest(
            query="test query",
            country="US",
            language="en",
            page=1
        )
        assert request.query == "test query"
        assert request.country == "US"
        assert request.language == "en"
        assert request.page == 1

    def test_invalid_country_code(self):
        """Test invalid country code validation."""
        with pytest.raises(ValueError, match="Country code must be 2-letter uppercase"):
            SearchRequest(
                query="test",
                country="usa",  # Invalid: should be "US"
                language="en",
                page=1
            )

    def test_invalid_language_code(self):
        """Test invalid language code validation."""
        with pytest.raises(ValueError, match="Language code must be 2-letter lowercase"):
            SearchRequest(
                query="test",
                country="US",
                language="EN",  # Invalid: should be "en"
                page=1
            )

    def test_empty_query(self):
        """Test empty query validation."""
        with pytest.raises(ValueError):
            SearchRequest(
                query="",  # Invalid: empty query
                country="US",
                language="en",
                page=1
            )

    def test_invalid_page_number(self):
        """Test invalid page number validation."""
        with pytest.raises(ValueError):
            SearchRequest(
                query="test",
                country="US",
                language="en",
                page=0  # Invalid: page must be >= 1
            )


class TestSearchResultValidation:
    """Test SearchResult model validation."""

    def test_valid_search_result(self):
        """Test valid search result creation."""
        result = SearchResult(
            rank=1,
            title="Test Title",
            url="https://example.com",
            description="Test description"
        )
        assert result.rank == 1
        assert result.title == "Test Title"
        assert str(result.url) == "https://example.com/"
        assert result.description == "Test description"

    def test_invalid_rank(self):
        """Test invalid rank validation."""
        with pytest.raises(ValueError):
            SearchResult(
                rank=0,  # Invalid: rank must be >= 1
                title="Test Title",
                url="https://example.com",
                description="Test description"
            )

    def test_invalid_url(self):
        """Test invalid URL validation."""
        with pytest.raises(ValueError):
            SearchResult(
                rank=1,
                title="Test Title",
                url="not-a-valid-url",  # Invalid URL
                description="Test description"
            )

    def test_optional_description(self):
        """Test optional description field."""
        result = SearchResult(
            rank=1,
            title="Test Title",
            url="https://example.com"
            # description is optional
        )
        assert result.description is None


if __name__ == "__main__":
    pytest.main([__file__])