"""Comprehensive unit tests for company router endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, UTC

from main import create_app
from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, CompanyInformation,
    CompanyBasicInfo, CompanyContact, CompanySocial, ExtractionMetadata,
    ExtractionError, ExtractionMode, SocialPlatformType
)
from app.utils.exceptions import CompanyAnalysisError


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_company_request():
    """Sample company information request."""
    return {
        "company_name": "OpenAI",
        "domain": "openai.com",
        "extraction_mode": "comprehensive",
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


@pytest.fixture
def sample_extraction_response():
    """Sample company extraction response."""
    company_info = CompanyInformation(
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
            phone="+1-415-555-0123",
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
    
    return CompanyExtractionResponse(
        request_id="req_12345678",
        company_name="OpenAI",
        success=True,
        company_information=company_info,
        extraction_metadata=ExtractionMetadata(
            pages_crawled=3,
            pages_attempted=5,
            extraction_time=25.5,
            sources_found=["https://openai.com", "https://openai.com/about"],
            search_queries_used=["OpenAI company information"],
            extraction_mode_used=ExtractionMode.COMPREHENSIVE
        ),
        errors=[],
        warnings=[],
        processing_time=27.1
    )


class TestCompanyExtractionEndpoint:
    """Test cases for the /api/v1/company/extract endpoint."""
    
    def test_extract_endpoint_exists(self, client):
        """Test that the extract endpoint is accessible."""
        response = client.post("/api/v1/company/extract", json={})
        # Should fail validation, not return 404
        assert response.status_code in [400, 422]
    
    @patch('app.services.company_service.CompanyExtractionService.extract_company_information')
    async def test_extract_company_information_success(
        self, mock_extract, client, sample_company_request, sample_extraction_response
    ):
        """Test successful company information extraction."""
        # Setup mock
        mock_extract.return_value = sample_extraction_response
        
        # Mock the async context manager
        with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.extract_company_information = AsyncMock(return_value=sample_extraction_response)
            mock_service.__aenter__ = AsyncMock(return_value=mock_service)
            mock_service.__aexit__ = AsyncMock()
            mock_service_class.return_value = mock_service
            
            response = client.post("/api/v1/company/extract", json=sample_company_request)
        
        # Assertions
        assert response.status_code == 200
        
        data = response.json()
        assert data["company_name"] == "OpenAI"
        assert data["success"] is True
        assert data["request_id"] == "req_12345678"
        
        # Check company information
        company_info = data["company_information"]
        assert company_info["basic_info"]["name"] == "OpenAI"
        assert company_info["basic_info"]["domain"] == "openai.com"
        assert company_info["contact"]["email"] == "contact@openai.com"
        assert len(company_info["social_media"]) == 1
        
        # Check metadata
        metadata = data["extraction_metadata"]
        assert metadata["pages_crawled"] == 3
        assert metadata["pages_attempted"] == 5
        assert metadata["extraction_mode_used"] == "comprehensive"
        
        # Check scores
        assert data["company_information"]["confidence_score"] == 0.85
        assert data["company_information"]["data_quality_score"] == 0.80
        assert data["company_information"]["completeness_score"] == 0.75
    
    def test_extract_validation_error_empty_company_name(self, client):
        """Test validation error for empty company name."""
        request_data = {
            "company_name": "",
            "extraction_mode": "basic"
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
        assert any("min_length" in str(detail) for detail in data["details"])
    
    def test_extract_validation_error_invalid_extraction_mode(self, client):
        """Test validation error for invalid extraction mode."""
        request_data = {
            "company_name": "TestCorp",
            "extraction_mode": "invalid_mode"
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_validation_error_invalid_country_code(self, client):
        """Test validation error for invalid country code."""
        request_data = {
            "company_name": "TestCorp",
            "country": "usa"  # Should be 2-letter uppercase
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_validation_error_invalid_language_code(self, client):
        """Test validation error for invalid language code."""
        request_data = {
            "company_name": "TestCorp",
            "language": "EN"  # Should be 2-letter lowercase
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_validation_error_invalid_pages_to_crawl(self, client):
        """Test validation error for invalid max_pages_to_crawl."""
        request_data = {
            "company_name": "TestCorp",
            "max_pages_to_crawl": 0  # Should be >= 1
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
        
        request_data["max_pages_to_crawl"] = 25  # Should be <= 20
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_validation_error_invalid_timeout(self, client):
        """Test validation error for invalid timeout."""
        request_data = {
            "company_name": "TestCorp",
            "timeout_seconds": 4  # Should be >= 5
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
        
        request_data["timeout_seconds"] = 125  # Should be <= 120
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_validation_error_invalid_domain(self, client):
        """Test validation error for invalid domain format."""
        request_data = {
            "company_name": "TestCorp",
            "domain": "not..a..valid..domain"
        }
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_error" in data["type"]
    
    def test_extract_with_defaults(self, client):
        """Test extraction with default parameters."""
        request_data = {
            "company_name": "TestCorp"
        }
        
        with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_response = CompanyExtractionResponse(
                request_id="test_12345678",
                company_name="TestCorp",
                success=True,
                company_information=CompanyInformation(
                    basic_info=CompanyBasicInfo(name="TestCorp")
                ),
                extraction_metadata=ExtractionMetadata(
                    pages_crawled=0,
                    pages_attempted=1,
                    extraction_time=5.0,
                    extraction_mode_used=ExtractionMode.COMPREHENSIVE
                ),
                processing_time=6.0
            )
            mock_service.extract_company_information = AsyncMock(return_value=mock_response)
            mock_service.__aenter__ = AsyncMock(return_value=mock_service)
            mock_service.__aexit__ = AsyncMock()
            mock_service_class.return_value = mock_service
            
            response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 200
        
        # Verify service was called with defaults
        mock_service.extract_company_information.assert_called_once()
        call_args = mock_service.extract_company_information.call_args[0][0]
        assert call_args.company_name == "TestCorp"
        assert call_args.extraction_mode == ExtractionMode.COMPREHENSIVE
        assert call_args.country == "US"
        assert call_args.language == "en"
        assert call_args.max_pages_to_crawl == 5
        assert call_args.timeout_seconds == 30
    
    @patch('app.services.company_service.CompanyExtractionService')
    def test_extract_company_analysis_error(self, mock_service_class, client):
        """Test company analysis error handling."""
        # Setup mock to raise CompanyAnalysisError
        mock_service = AsyncMock()
        mock_service.extract_company_information = AsyncMock(
            side_effect=CompanyAnalysisError("Analysis failed")
        )
        mock_service.__aenter__ = AsyncMock(return_value=mock_service)
        mock_service.__aexit__ = AsyncMock()
        mock_service_class.return_value = mock_service
        
        request_data = {"company_name": "TestCorp"}
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Analysis failed"
        assert data["type"] == "company_analysis_error"
    
    @patch('app.services.company_service.CompanyExtractionService')
    def test_extract_unexpected_error(self, mock_service_class, client):
        """Test unexpected error handling."""
        # Setup mock to raise unexpected error
        mock_service = AsyncMock()
        mock_service.extract_company_information = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        mock_service.__aenter__ = AsyncMock(return_value=mock_service)
        mock_service.__aexit__ = AsyncMock()
        mock_service_class.return_value = mock_service
        
        request_data = {"company_name": "TestCorp"}
        
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Internal server error"
        assert data["type"] == "server_error"
    
    def test_extract_different_extraction_modes(self, client):
        """Test extraction with different extraction modes."""
        modes = ["basic", "comprehensive", "contact_focused", "financial_focused"]
        
        for mode in modes:
            request_data = {
                "company_name": "TestCorp",
                "extraction_mode": mode
            }
            
            with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
                mock_service = AsyncMock()
                mock_response = CompanyExtractionResponse(
                    request_id="test_12345678",
                    company_name="TestCorp",
                    success=True,
                    company_information=CompanyInformation(
                        basic_info=CompanyBasicInfo(name="TestCorp")
                    ),
                    extraction_metadata=ExtractionMetadata(
                        pages_crawled=1,
                        pages_attempted=1,
                        extraction_time=10.0,
                        extraction_mode_used=getattr(ExtractionMode, mode.upper())
                    ),
                    processing_time=11.0
                )
                mock_service.extract_company_information = AsyncMock(return_value=mock_response)
                mock_service.__aenter__ = AsyncMock(return_value=mock_service)
                mock_service.__aexit__ = AsyncMock()
                mock_service_class.return_value = mock_service
                
                response = client.post("/api/v1/company/extract", json=request_data)
            
            assert response.status_code == 200
            
            # Verify correct mode was passed
            mock_service.extract_company_information.assert_called_once()
            call_args = mock_service.extract_company_information.call_args[0][0]
            assert call_args.extraction_mode.value == mode
    
    def test_extract_different_countries_languages(self, client):
        """Test extraction with different country and language combinations."""
        test_cases = [
            {"country": "GB", "language": "en"},
            {"country": "FR", "language": "fr"},
            {"country": "DE", "language": "de"},
            {"country": "JP", "language": "ja"},
        ]
        
        for case in test_cases:
            request_data = {
                "company_name": "TestCorp",
                **case
            }
            
            with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
                mock_service = AsyncMock()
                mock_response = CompanyExtractionResponse(
                    request_id="test_12345678",
                    company_name="TestCorp",
                    success=True,
                    company_information=CompanyInformation(
                        basic_info=CompanyBasicInfo(name="TestCorp")
                    ),
                    extraction_metadata=ExtractionMetadata(
                        pages_crawled=1,
                        pages_attempted=1,
                        extraction_time=10.0,
                        extraction_mode_used=ExtractionMode.COMPREHENSIVE
                    ),
                    processing_time=11.0
                )
                mock_service.extract_company_information = AsyncMock(return_value=mock_response)
                mock_service.__aenter__ = AsyncMock(return_value=mock_service)
                mock_service.__aexit__ = AsyncMock()
                mock_service_class.return_value = mock_service
                
                response = client.post("/api/v1/company/extract", json=request_data)
            
            assert response.status_code == 200
            
            # Verify correct parameters were passed
            mock_service.extract_company_information.assert_called_once()
            call_args = mock_service.extract_company_information.call_args[0][0]
            assert call_args.country == case["country"]
            assert call_args.language == case["language"]
    
    def test_extract_various_configurations(self, client):
        """Test extraction with various configuration combinations."""
        configurations = [
            {
                "include_subsidiaries": True,
                "include_social_media": False,
                "include_financial_data": False,
                "include_contact_info": True,
                "include_key_personnel": False,
                "max_pages_to_crawl": 3,
                "timeout_seconds": 60
            },
            {
                "include_subsidiaries": False,
                "include_social_media": True,
                "include_financial_data": True,
                "include_contact_info": False,
                "include_key_personnel": True,
                "max_pages_to_crawl": 10,
                "timeout_seconds": 90
            }
        ]
        
        for config in configurations:
            request_data = {
                "company_name": "TestCorp",
                **config
            }
            
            with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
                mock_service = AsyncMock()
                mock_response = CompanyExtractionResponse(
                    request_id="test_12345678",
                    company_name="TestCorp",
                    success=True,
                    company_information=CompanyInformation(
                        basic_info=CompanyBasicInfo(name="TestCorp")
                    ),
                    extraction_metadata=ExtractionMetadata(
                        pages_crawled=1,
                        pages_attempted=1,
                        extraction_time=10.0,
                        extraction_mode_used=ExtractionMode.COMPREHENSIVE
                    ),
                    processing_time=11.0
                )
                mock_service.extract_company_information = AsyncMock(return_value=mock_response)
                mock_service.__aenter__ = AsyncMock(return_value=mock_service)
                mock_service.__aexit__ = AsyncMock()
                mock_service_class.return_value = mock_service
                
                response = client.post("/api/v1/company/extract", json=request_data)
            
            assert response.status_code == 200
            
            # Verify all configuration options were passed correctly
            mock_service.extract_company_information.assert_called_once()
            call_args = mock_service.extract_company_information.call_args[0][0]
            
            for key, value in config.items():
                assert getattr(call_args, key) == value
    
    def test_extract_failed_extraction_response(self, client):
        """Test response when extraction fails but doesn't raise exception."""
        failed_response = CompanyExtractionResponse(
            request_id="req_failed123",
            company_name="FailedCorp",
            success=False,
            company_information=None,
            extraction_metadata=ExtractionMetadata(
                pages_crawled=0,
                pages_attempted=3,
                extraction_time=15.0,
                extraction_mode_used=ExtractionMode.BASIC
            ),
            errors=[
                ExtractionError(
                    error_type="SearchError",
                    error_message="No search results found",
                    url=None
                ),
                ExtractionError(
                    error_type="TimeoutError",
                    error_message="Request timed out",
                    url="https://failedcorp.com"
                )
            ],
            warnings=["Limited data availability", "Incomplete information"],
            processing_time=16.5
        )
        
        with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.extract_company_information = AsyncMock(return_value=failed_response)
            mock_service.__aenter__ = AsyncMock(return_value=mock_service)
            mock_service.__aexit__ = AsyncMock()
            mock_service_class.return_value = mock_service
            
            request_data = {"company_name": "FailedCorp"}
            response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 200  # Still returns 200 for controlled failure
        
        data = response.json()
        assert data["success"] is False
        assert data["company_information"] is None
        assert len(data["errors"]) == 2
        assert len(data["warnings"]) == 2
        assert data["errors"][0]["error_type"] == "SearchError"
        assert data["errors"][1]["error_type"] == "TimeoutError"
        assert "Limited data availability" in data["warnings"]


class TestCompanyStatusEndpoint:
    """Test cases for the /api/v1/company/status endpoint."""
    
    def test_status_endpoint_exists(self, client):
        """Test that the status endpoint is accessible."""
        response = client.get("/api/v1/company/status")
        
        # Should return status information
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data
    
    @patch('app.services.company_service.CompanyExtractionService.get_service_status')
    def test_status_success(self, mock_get_status, client):
        """Test successful status check."""
        mock_status = {
            "status": "operational",
            "service_version": "1.0.0",
            "serp_service_initialized": True,
            "crawl_service_initialized": True,
            "parser_initialized": True,
            "dependencies": {
                "serp_service": "operational",
                "crawl_service": "operational"
            }
        }
        
        with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_service_status = AsyncMock(return_value=mock_status)
            mock_service_class.return_value = mock_service
            
            response = client.get("/api/v1/company/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "company_extraction_api"
        assert data["status"] == "operational"
        assert data["serp_service_initialized"] is True
        assert data["crawl_service_initialized"] is True
        assert data["parser_initialized"] is True
        assert "dependencies" in data
    
    @patch('app.services.company_service.CompanyExtractionService')
    def test_status_service_error(self, mock_service_class, client):
        """Test status when service initialization fails."""
        # Setup mock to raise error
        mock_service_class.side_effect = Exception("Service initialization failed")
        
        response = client.get("/api/v1/company/status")
        
        assert response.status_code == 503
        data = response.json()
        assert data["service"] == "company_extraction_api"
        assert data["status"] == "error"
        assert "error" in data
        assert "Service initialization failed" in data["error"]


class TestRequestResponseValidation:
    """Test request/response validation through the API."""
    
    def test_request_model_validation_comprehensive(self, client):
        """Test that request model validation works through the API."""
        valid_requests = [
            {
                "company_name": "TestCorp",
                "domain": "testcorp.com",
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
            },
            {
                "company_name": "MinimalCorp"  # Minimal request with defaults
            },
            {
                "company_name": "ConfigCorp",
                "extraction_mode": "basic",
                "max_pages_to_crawl": 1,
                "timeout_seconds": 10
            }
        ]
        
        for request_data in valid_requests:
            # Mock successful response for validation test
            with patch('app.services.company_service.CompanyExtractionService') as mock_service_class:
                mock_service = AsyncMock()
                mock_response = CompanyExtractionResponse(
                    request_id="test_valid",
                    company_name=request_data["company_name"],
                    success=True,
                    company_information=CompanyInformation(
                        basic_info=CompanyBasicInfo(name=request_data["company_name"])
                    ),
                    extraction_metadata=ExtractionMetadata(
                        pages_crawled=1,
                        pages_attempted=1,
                        extraction_time=5.0,
                        extraction_mode_used=ExtractionMode.COMPREHENSIVE
                    ),
                    processing_time=6.0
                )
                mock_service.extract_company_information = AsyncMock(return_value=mock_response)
                mock_service.__aenter__ = AsyncMock(return_value=mock_service)
                mock_service.__aexit__ = AsyncMock()
                mock_service_class.return_value = mock_service
                
                response = client.post("/api/v1/company/extract", json=request_data)
            
            # Should not fail validation
            assert response.status_code == 200, f"Request failed validation: {request_data}"
    
    def test_request_model_validation_invalid_cases(self, client):
        """Test invalid request data is properly rejected."""
        invalid_requests = [
            {"company_name": ""},  # Empty company name
            {"company_name": "Test", "country": "usa"},  # Invalid country format
            {"company_name": "Test", "language": "EN"},  # Invalid language format
            {"company_name": "Test", "max_pages_to_crawl": 0},  # Invalid max pages
            {"company_name": "Test", "max_pages_to_crawl": 25},  # Max pages too high
            {"company_name": "Test", "timeout_seconds": 3},  # Timeout too low
            {"company_name": "Test", "timeout_seconds": 150},  # Timeout too high
            {"company_name": "Test", "domain": "not..valid"},  # Invalid domain
            {"company_name": "Test", "extraction_mode": "invalid"},  # Invalid mode
            {"country": "US"},  # Missing company name
        ]
        
        for request_data in invalid_requests:
            response = client.post("/api/v1/company/extract", json=request_data)
            assert response.status_code == 422, f"Request should have failed validation: {request_data}"
            data = response.json()
            assert data["type"] == "validation_error"


class TestErrorHandlingIntegration:
    """Test error handling integration through the router."""
    
    @patch('app.services.company_service.CompanyExtractionService')
    def test_service_timeout_error_handling(self, mock_service_class, client):
        """Test handling of service timeout errors."""
        mock_service = AsyncMock()
        mock_service.extract_company_information = AsyncMock(
            side_effect=asyncio.TimeoutError("Operation timed out")
        )
        mock_service.__aenter__ = AsyncMock(return_value=mock_service)
        mock_service.__aexit__ = AsyncMock()
        mock_service_class.return_value = mock_service
        
        request_data = {"company_name": "TimeoutCorp"}
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["type"] == "server_error"
    
    @patch('app.services.company_service.CompanyExtractionService')  
    def test_service_connection_error_handling(self, mock_service_class, client):
        """Test handling of service connection errors."""
        mock_service = AsyncMock()
        mock_service.extract_company_information = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )
        mock_service.__aenter__ = AsyncMock(return_value=mock_service)
        mock_service.__aexit__ = AsyncMock()
        mock_service_class.return_value = mock_service
        
        request_data = {"company_name": "ConnectionCorp"}
        response = client.post("/api/v1/company/extract", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["type"] == "server_error"
    
    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        # Send malformed JSON
        response = client.post(
            "/api/v1/company/extract",
            content='{"company_name": "TestCorp", invalid json}',
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])