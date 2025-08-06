"""Tests for the search API endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, UTC

from main import create_app
from app.models.serp import SearchRequest, SearchResponse, SearchResult
from app.clients.bright_data import (
    BrightDataError,
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_search_response():
    """Create mock search response."""
    return SearchResponse(
        query="test query",
        results_count=2,
        organic_results=[
            SearchResult(
                rank=1,
                title="Test Result 1",
                url="https://example.com/1",
                description="Test description 1"
            ),
            SearchResult(
                rank=2,
                title="Test Result 2", 
                url="https://example.com/2",
                description="Test description 2"
            )
        ],
        timestamp=datetime.now(UTC),
        search_metadata={
            "search_time": 0.5,
            "country": "US",
            "language": "en"
        }
    )


class TestSearchEndpoint:
    """Test cases for the /api/v1/search endpoint."""
    
    def test_search_endpoint_exists(self, client):
        """Test that the search endpoint is accessible."""
        # Test with invalid data to ensure endpoint exists
        response = client.post("/api/v1/search", json={})
        assert response.status_code in [400, 422]  # Should fail validation, not 404
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_success(self, mock_search, client, mock_search_response):
        """Test successful search request."""
        # Setup mock
        mock_search.return_value = mock_search_response
        
        # Make request
        request_data = {
            "query": "test query",
            "country": "US",
            "language": "en",
            "page": 1
        }
        
        response = client.post("/api/v1/search", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "test query"
        assert data["results_count"] == 2
        assert len(data["organic_results"]) == 2
        assert data["organic_results"][0]["title"] == "Test Result 1"
        assert data["organic_results"][0]["url"] == "https://example.com/1"
        assert "timestamp" in data
        assert "search_metadata" in data
        
        # Verify mock was called correctly
        mock_search.assert_called_once()
        call_args = mock_search.call_args[0][0]
        assert call_args.query == "test query"
        assert call_args.country == "US"
        assert call_args.language == "en"
        assert call_args.page == 1
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_with_defaults(self, mock_search, client, mock_search_response):
        """Test search request with default parameters."""
        # Setup mock
        mock_search.return_value = mock_search_response
        
        # Make request with minimal data
        request_data = {"query": "test query"}
        
        response = client.post("/api/v1/search", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        
        # Verify defaults were applied
        call_args = mock_search.call_args[0][0]
        assert call_args.query == "test query"
        assert call_args.country == "US"  # Default
        assert call_args.language == "en"  # Default  
        assert call_args.page == 1  # Default
    
    def test_search_validation_error_empty_query(self, client):
        """Test validation error for empty query."""
        request_data = {"query": ""}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
        assert any("min_length" in str(error) for error in data["details"])
    
    def test_search_validation_error_invalid_country(self, client):
        """Test validation error for invalid country code."""
        request_data = {
            "query": "test",
            "country": "usa"  # Should be 2-letter uppercase
        }
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_search_validation_error_invalid_language(self, client):
        """Test validation error for invalid language code."""
        request_data = {
            "query": "test",
            "language": "EN"  # Should be 2-letter lowercase
        }
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_search_validation_error_invalid_page(self, client):
        """Test validation error for invalid page number."""
        request_data = {
            "query": "test",
            "page": 0  # Should be >= 1
        }
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_rate_limit_error(self, mock_search, client):
        """Test rate limit error handling."""
        # Setup mock to raise rate limit error
        mock_search.side_effect = BrightDataRateLimitError("Rate limit exceeded")
        
        request_data = {"query": "test query"}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "Rate limit exceeded"
        assert data["type"] == "rate_limit_error"
        assert "Retry-After" in response.headers
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_timeout_error(self, mock_search, client):
        """Test timeout error handling."""
        # Setup mock to raise timeout error
        mock_search.side_effect = BrightDataTimeoutError("Request timeout")
        
        request_data = {"query": "test query"}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 504
        data = response.json()
        assert data["error"] == "Request timeout"
        assert data["type"] == "timeout_error"
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_api_error(self, mock_search, client):
        """Test API error handling."""
        # Setup mock to raise API error
        mock_search.side_effect = BrightDataError("API error")
        
        request_data = {"query": "test query"}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "External API error"
        assert data["type"] == "api_error"
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_unexpected_error(self, mock_search, client):
        """Test unexpected error handling."""
        # Setup mock to raise unexpected error
        mock_search.side_effect = Exception("Unexpected error")
        
        request_data = {"query": "test query"}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert data["type"] == "server_error"
    
    def test_search_missing_query(self, client):
        """Test request with missing query field."""
        request_data = {}
        
        response = client.post("/api/v1/search", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_different_countries_languages(self, mock_search, client, mock_search_response):
        """Test search with different country and language combinations."""
        # Setup mock
        mock_search.return_value = mock_search_response
        
        test_cases = [
            {"query": "test", "country": "GB", "language": "en"},
            {"query": "test", "country": "FR", "language": "fr"},
            {"query": "test", "country": "DE", "language": "de"},
            {"query": "test", "country": "JP", "language": "ja"},
        ]
        
        for case in test_cases:
            response = client.post("/api/v1/search", json=case)
            assert response.status_code == 200
            
            # Verify correct parameters were passed
            call_args = mock_search.call_args[0][0]
            assert call_args.country == case["country"]
            assert call_args.language == case["language"]
    
    @patch('app.services.serp_service.SERPService.search')
    def test_search_pagination(self, mock_search, client, mock_search_response):
        """Test search with different page numbers."""
        # Setup mock
        mock_search.return_value = mock_search_response
        
        for page in [1, 2, 5, 10]:
            request_data = {"query": "test", "page": page}
            response = client.post("/api/v1/search", json=request_data)
            
            assert response.status_code == 200
            
            # Verify correct page was passed
            call_args = mock_search.call_args[0][0]
            assert call_args.page == page


class TestSearchStatusEndpoint:
    """Test cases for the /api/v1/search/status endpoint."""
    
    def test_search_status_success(self, client):
        """Test successful search status check."""
        response = client.get("/api/v1/search/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "search_api"
        assert "status" in data
        assert "dependencies" in data
    
    @patch('app.services.serp_service.SERPService.__init__')
    def test_search_status_service_error(self, mock_init, client):
        """Test search status when service initialization fails."""
        # Setup mock to raise error
        mock_init.side_effect = Exception("Service initialization failed")
        
        response = client.get("/api/v1/search/status")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["service"] == "search_api"
        assert "error" in data


class TestSearchIntegration:
    """Integration tests for the search functionality."""
    
    @patch('app.clients.bright_data.BrightDataClient.search')
    def test_full_integration_mock(self, mock_client_search, client):
        """Test full integration with mocked Bright Data client."""
        # Create a realistic mock response from the client
        mock_client_response = SearchResponse(
            query="python programming",
            results_count=3,
            organic_results=[
                SearchResult(
                    rank=1,
                    title="Learn Python Programming",
                    url="https://python.org/learn",
                    description="Official Python learning resources"
                ),
                SearchResult(
                    rank=2,
                    title="Python Tutorial for Beginners",
                    url="https://tutorial.python.org",
                    description="Comprehensive Python tutorial"
                ),
                SearchResult(
                    rank=3,
                    title="Python Documentation",
                    url="https://docs.python.org",
                    description="Official Python documentation"
                )
            ],
            search_metadata={"parsed_from": "html", "content_length": 50000}
        )
        
        mock_client_search.return_value = mock_client_response
        
        # Make request
        request_data = {
            "query": "python programming",
            "country": "US", 
            "language": "en",
            "page": 1
        }
        
        response = client.post("/api/v1/search", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "python programming"
        assert data["results_count"] == 3
        assert len(data["organic_results"]) == 3
        
        # Check that service enhanced the response
        assert "search_time" in data["search_metadata"]
        assert "service_version" in data["search_metadata"]
        assert "enhanced_processing" in data["search_metadata"]
        
        # Verify client was called correctly
        mock_client_search.assert_called_once()
        search_request = mock_client_search.call_args[0][0]
        assert search_request.query == "python programming"
        assert search_request.country == "US"
        assert search_request.language == "en"
        assert search_request.page == 1


class TestRequestResponseModels:
    """Test the request and response models work correctly with the API."""
    
    def test_search_request_model_validation(self, client):
        """Test that SearchRequest model validation works through the API."""
        valid_requests = [
            {"query": "test", "country": "US", "language": "en", "page": 1},
            {"query": "test"},  # Uses defaults
            {"query": "test", "country": "GB"},
            {"query": "test", "language": "fr"},
            {"query": "test", "page": 5},
        ]
        
        for request_data in valid_requests:
            response = client.post("/api/v1/search", json=request_data)
            # Should not fail validation (might fail for other reasons)
            assert response.status_code != 422
    
    def test_search_request_invalid_data(self, client):
        """Test invalid request data is properly rejected."""
        invalid_requests = [
            {"query": ""},  # Empty query
            {"query": "test", "country": "usa"},  # Invalid country format
            {"query": "test", "language": "EN"},  # Invalid language format
            {"query": "test", "page": 0},  # Invalid page number
            {"query": "test", "page": -1},  # Negative page number
            {"country": "US"},  # Missing query
        ]
        
        for request_data in invalid_requests:
            response = client.post("/api/v1/search", json=request_data)
            assert response.status_code == 422
            data = response.json()
            assert data["type"] == "validation_error"


if __name__ == "__main__":
    pytest.main([__file__])