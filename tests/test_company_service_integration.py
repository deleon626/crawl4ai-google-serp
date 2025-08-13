"""Integration test for CompanyExtractionService - demonstrates real usage."""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.services.company_service import CompanyExtractionService
from app.models.company import CompanyInformationRequest, ExtractionMode


class TestCompanyExtractionServiceIntegration:
    """Integration tests for CompanyExtractionService."""
    
    @pytest.mark.asyncio
    async def test_service_with_mocked_dependencies(self):
        """Test the full service workflow with mocked dependencies."""
        # Create a comprehensive request
        request = CompanyInformationRequest(
            company_name="TechCorp Inc",
            domain="techcorp.com",
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            country="US",
            language="en",
            max_pages_to_crawl=2,
            timeout_seconds=15
        )
        
        # Mock the actual external services
        mock_search_response_data = {
            "query": "TechCorp Inc company information",
            "results_count": 2,
            "organic_results": [
                {
                    "rank": 1,
                    "title": "TechCorp Inc - About Us",
                    "url": "https://techcorp.com/about",
                    "description": "TechCorp Inc is a leading technology company."
                },
                {
                    "rank": 2,
                    "title": "TechCorp Inc - Contact",
                    "url": "https://techcorp.com/contact",
                    "description": "Contact TechCorp Inc for business inquiries."
                }
            ]
        }
        
        mock_crawl_response_data = {
            "success": True,
            "result": {
                "url": "https://techcorp.com/about",
                "title": "TechCorp Inc - About Us", 
                "cleaned_html": """
                <html><body>
                    <h1>TechCorp Inc</h1>
                    <p>TechCorp Inc is a leading technology company founded in 2010.</p>
                    <p>Contact us at info@techcorp.com or call +1-555-123-4567</p>
                    <p>Our headquarters is located at 123 Tech Street, San Francisco, CA 94105</p>
                    <a href="https://linkedin.com/company/techcorp">LinkedIn</a>
                </body></html>
                """,
                "metadata": {"word_count": 150}
            },
            "execution_time": 2.1
        }
        
        service = CompanyExtractionService()
        
        # Mock the external dependencies
        with patch('app.services.company_service.SERPService') as mock_serp_class, \
             patch('app.services.company_service.CrawlService') as mock_crawl_class:
            
            # Create mock instances
            mock_serp_instance = AsyncMock()
            mock_crawl_instance = AsyncMock()
            
            # Configure mock classes to return instances
            mock_serp_class.return_value = mock_serp_instance
            mock_crawl_class.return_value = mock_crawl_instance
            
            # Configure mock SERP service
            mock_search_response = AsyncMock()
            mock_search_response.organic_results = []
            for result_data in mock_search_response_data["organic_results"]:
                mock_result = AsyncMock()
                mock_result.url = result_data["url"]
                mock_result.title = result_data["title"]
                mock_result.description = result_data["description"]
                mock_search_response.organic_results.append(mock_result)
            
            mock_serp_instance.search = AsyncMock(return_value=mock_search_response)
            
            # Configure mock crawl service
            mock_crawl_response = AsyncMock()
            mock_crawl_response.success = True
            mock_crawl_response.result = AsyncMock()
            mock_crawl_response.result.cleaned_html = mock_crawl_response_data["result"]["cleaned_html"]
            mock_crawl_response.result.title = mock_crawl_response_data["result"]["title"]
            mock_crawl_response.result.metadata = mock_crawl_response_data["result"]["metadata"]
            mock_crawl_response.execution_time = mock_crawl_response_data["execution_time"]
            
            mock_crawl_instance.crawl = AsyncMock(return_value=mock_crawl_response)
            
            # Execute the service
            async with service:
                response = await service.extract_company_information(request)
            
            # Validate response structure
            assert response is not None
            assert response.company_name == "TechCorp Inc"
            assert isinstance(response.success, bool)
            assert response.processing_time > 0
            assert response.extraction_metadata is not None
            assert response.extraction_metadata.extraction_mode_used == ExtractionMode.COMPREHENSIVE
            
            # Validate that services were called
            mock_serp_instance.search.assert_called()
            mock_crawl_instance.crawl.assert_called()
            
            print(f"✅ Integration test passed!")
            print(f"   - Company: {response.company_name}")
            print(f"   - Success: {response.success}")
            print(f"   - Processing time: {response.processing_time:.2f}s")
            print(f"   - Pages attempted: {response.extraction_metadata.pages_attempted}")
            print(f"   - Pages crawled: {response.extraction_metadata.pages_crawled}")
            print(f"   - Errors: {len(response.errors)}")
            print(f"   - Warnings: {len(response.warnings)}")
            
            if response.company_information:
                print(f"   - Company info extracted: ✅")
                print(f"   - Confidence: {response.company_information.confidence_score}")
            else:
                print(f"   - Company info extracted: ❌")
    
    def test_service_creation_and_basic_properties(self):
        """Test that service can be created and has expected properties."""
        service = CompanyExtractionService()
        
        # Check initial state
        assert service.serp_service is None
        assert service.crawl_service is None
        assert service.company_parser is not None
        
        # Check service methods exist
        assert hasattr(service, 'extract_company_information')
        assert hasattr(service, 'get_service_status')
        assert hasattr(service, '_generate_search_queries')
        assert hasattr(service, '_score_url_priority')
        assert hasattr(service, '_aggregate_company_information')
        
        print("✅ Service creation and basic properties test passed!")
    
    def test_search_query_generation_comprehensive(self):
        """Test search query generation for different modes."""
        service = CompanyExtractionService()
        
        # Test comprehensive mode with all features enabled
        request = CompanyInformationRequest(
            company_name="Innovation Labs",
            domain="innovationlabs.io",
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            include_social_media=True,
            include_financial_data=True,
            include_contact_info=True,
            include_key_personnel=True
        )
        
        queries = service._generate_search_queries(request)
        
        # Should generate multiple types of queries
        assert len(queries) > 8  # Comprehensive should have many queries
        
        # Should include domain-specific query
        domain_queries = [q for q in queries if 'site:innovationlabs.io' in q]
        assert len(domain_queries) > 0
        
        # Should include contact queries
        contact_queries = [q for q in queries if 'contact' in q.lower()]
        assert len(contact_queries) > 0
        
        # Should include social media queries
        social_queries = [q for q in queries if any(platform in q.lower() for platform in ['linkedin', 'twitter'])]
        assert len(social_queries) > 0
        
        # Should include financial queries
        financial_queries = [q for q in queries if any(term in q.lower() for term in ['funding', 'revenue', 'crunchbase'])]
        assert len(financial_queries) > 0
        
        # Should include personnel queries
        personnel_queries = [q for q in queries if any(term in q.lower() for term in ['ceo', 'founder', 'leadership'])]
        assert len(personnel_queries) > 0
        
        print("✅ Comprehensive search query generation test passed!")
        print(f"   - Total queries: {len(queries)}")
        print(f"   - Domain queries: {len(domain_queries)}")
        print(f"   - Contact queries: {len(contact_queries)}")
        print(f"   - Social queries: {len(social_queries)}")
        print(f"   - Financial queries: {len(financial_queries)}")
        print(f"   - Personnel queries: {len(personnel_queries)}")
    
    def test_url_priority_scoring_comprehensive(self):
        """Test URL priority scoring for various scenarios."""
        service = CompanyExtractionService()
        
        request = CompanyInformationRequest(
            company_name="DataCorp",
            domain="datacorp.com"
        )
        
        # Test scenarios with expected relative priorities
        test_urls = [
            # Official domain pages (should be highest)
            ("https://datacorp.com/about", "DataCorp - About Us", "Learn about DataCorp company", "high"),
            ("https://datacorp.com/contact", "DataCorp - Contact", "Contact DataCorp team", "high"),
            
            # High-value third-party domains (should be medium-high)
            ("https://linkedin.com/company/datacorp", "DataCorp | LinkedIn", "DataCorp company profile", "medium-high"),
            ("https://crunchbase.com/organization/datacorp", "DataCorp - Crunchbase", "DataCorp funding info", "medium-high"),
            
            # General third-party (should be lower)
            ("https://example-news.com/datacorp-article", "DataCorp in the News", "Article about DataCorp", "medium"),
            
            # Social media (should be lower due to penalty)
            ("https://facebook.com/datacorp", "DataCorp on Facebook", "DataCorp Facebook page", "low"),
        ]
        
        scores = {}
        for url, title, description, expected_tier in test_urls:
            score = service._score_url_priority(url, title, description, request)
            scores[expected_tier] = scores.get(expected_tier, [])
            scores[expected_tier].append(score)
            print(f"   - {url}: {score:.3f} (expected: {expected_tier})")
        
        # Validate relative priorities
        if "high" in scores and "medium-high" in scores:
            assert max(scores["high"]) >= max(scores["medium-high"])
        
        if "medium-high" in scores and "medium" in scores:
            assert max(scores["medium-high"]) >= max(scores["medium"])
        
        if "medium" in scores and "low" in scores:
            assert max(scores["medium"]) >= max(scores["low"])
        
        print("✅ URL priority scoring test passed!")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])