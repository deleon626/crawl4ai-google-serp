"""
Tests for Company Analysis Service functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.company_analysis_service import CompanyAnalysisService, CompanyWebsiteDiscovery, EmployeeExtractor
from app.models.company import (
    CompanyAnalysisRequest, CompanyAnalysisResponse, EmployeeProfile, 
    EmployeeRole, WebsiteDiscovery, CompanyInfo
)
from app.utils.exceptions import CompanyAnalysisError


class TestCompanyWebsiteDiscovery:
    """Test CompanyWebsiteDiscovery class."""
    
    def test_generate_search_queries(self):
        """Test search query generation."""
        discovery = CompanyWebsiteDiscovery()
        
        queries = discovery.generate_search_queries("Acme Corp", "technology")
        
        assert len(queries) >= 4
        assert any("official website" in query for query in queries)
        assert any("company website" in query for query in queries)
        assert any("linkedin.com/company" in query for query in queries)
        assert any("technology" in query for query in queries)
    
    def test_extract_company_urls(self):
        """Test URL extraction from SERP results."""
        discovery = CompanyWebsiteDiscovery()
        
        mock_results = [
            {
                'link': 'https://acmecorp.com',
                'title': 'Acme Corp - Official Company Website',
                'snippet': 'Leading technology solutions provider'
            },
            {
                'link': 'https://linkedin.com/company/acme-corp',
                'title': 'Acme Corp | LinkedIn',
                'snippet': 'Follow Acme Corp on LinkedIn'
            },
            {
                'link': 'https://facebook.com/acmecorp',
                'title': 'Acme Corp - Facebook',
                'snippet': 'Connect with Acme Corp on Facebook'
            },
            {
                'link': 'https://glassdoor.com/Overview/Working-at-acme',
                'title': 'Working at Acme Corp - Glassdoor',
                'snippet': 'Employee reviews for Acme Corp'
            }
        ]
        
        primary, alternatives, social = discovery.extract_company_urls(mock_results)
        
        assert primary == 'https://acmecorp.com'
        assert 'linkedin' in social
        assert 'facebook' in social
        assert social['linkedin'] == 'https://linkedin.com/company/acme-corp'
    
    def test_is_likely_company_website(self):
        """Test company website detection."""
        discovery = CompanyWebsiteDiscovery()
        
        # Should detect as company website
        assert discovery._is_likely_company_website(
            'https://acmecorp.com',
            'Acme Corp - Official Company Website', 
            'Leading technology solutions'
        )
        
        # Should not detect social media as company website
        assert not discovery._is_likely_company_website(
            'https://linkedin.com/company/acme',
            'Acme Corp | LinkedIn',
            'Follow us on LinkedIn'
        )


class TestEmployeeExtractor:
    """Test EmployeeExtractor class."""
    
    def test_extract_employees_from_content(self):
        """Test employee extraction from content."""
        extractor = EmployeeExtractor()
        
        content = """
        <div class="team-section">
            <h2>Our Leadership Team</h2>
            <div class="employee">
                <h3>John Smith</h3>
                <p>Chief Executive Officer</p>
                <p>John leads our company with over 15 years of experience.</p>
            </div>
            <div class="employee">
                <h3>Jane Doe</h3>
                <p>Chief Technology Officer</p>
                <p>Jane oversees our technology strategy and development.</p>
            </div>
            <div class="employee">
                <h3>Bob Wilson</h3>
                <p>Senior Engineer</p>
                <p>Bob is responsible for our core platform development.</p>
            </div>
        </div>
        """
        
        employees = extractor.extract_employees(content, "https://acmecorp.com/team")
        
        assert len(employees) >= 2  # Should find at least CEO and CTO
        
        # Check for executive roles
        executive_names = [emp.name for emp in employees if emp.role_category == EmployeeRole.EXECUTIVE]
        assert len(executive_names) >= 2
        
        # Check confidence scores
        for employee in employees:
            assert 0.0 <= employee.confidence_score <= 1.0
            assert employee.source_url == "https://acmecorp.com/team"
    
    def test_categorize_role(self):
        """Test role categorization."""
        extractor = EmployeeExtractor()
        
        assert extractor._categorize_role("CEO") == EmployeeRole.EXECUTIVE
        assert extractor._categorize_role("Chief Technology Officer") == EmployeeRole.EXECUTIVE
        assert extractor._categorize_role("Senior Manager") == EmployeeRole.MANAGEMENT
        assert extractor._categorize_role("Software Engineer") == EmployeeRole.ENGINEERING
        assert extractor._categorize_role("Sales Representative") == EmployeeRole.SALES
        assert extractor._categorize_role("Marketing Specialist") == EmployeeRole.MARKETING
        assert extractor._categorize_role("Random Title") == EmployeeRole.OTHER
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        extractor = EmployeeExtractor()
        
        # Executive should have high confidence
        exec_confidence = extractor._calculate_confidence(
            "John Smith", "CEO", "https://company.com/team"
        )
        assert exec_confidence > 0.7
        
        # Generic role should have lower confidence
        generic_confidence = extractor._calculate_confidence(
            "Jane Doe", "Employee", "https://company.com/about"
        )
        assert generic_confidence < exec_confidence
    
    def test_deduplicate_and_score(self):
        """Test employee deduplication."""
        extractor = EmployeeExtractor()
        
        employees = [
            EmployeeProfile(
                name="John Smith",
                title="CEO",
                role_category=EmployeeRole.EXECUTIVE,
                confidence_score=0.9,
                source_url="https://company.com/team"
            ),
            EmployeeProfile(
                name="john smith",  # Same name, different case
                title="Chief Executive Officer",
                role_category=EmployeeRole.EXECUTIVE,
                confidence_score=0.8,
                source_url="https://company.com/about"
            ),
            EmployeeProfile(
                name="Jane Doe",
                title="CTO",
                role_category=EmployeeRole.EXECUTIVE,
                confidence_score=0.85,
                source_url="https://company.com/team"
            )
        ]
        
        unique_employees = extractor._deduplicate_and_score(employees)
        
        assert len(unique_employees) == 2  # Should deduplicate John Smith
        assert unique_employees[0].confidence_score >= unique_employees[1].confidence_score  # Should be sorted by confidence


class TestCompanyAnalysisService:
    """Test CompanyAnalysisService class."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return CompanyAnalysisService()
    
    @pytest.fixture
    def mock_serp_response(self):
        """Mock SERP response."""
        return {
            "success": True,
            "results": [
                {
                    'link': 'https://acmecorp.com',
                    'title': 'Acme Corp - Official Website',
                    'snippet': 'Leading technology solutions provider'
                },
                {
                    'link': 'https://linkedin.com/company/acme-corp',
                    'title': 'Acme Corp | LinkedIn',
                    'snippet': 'Follow Acme Corp on LinkedIn'
                }
            ],
            "total_results": 2
        }
    
    @pytest.fixture
    def mock_crawl_response(self):
        """Mock crawl response."""
        return {
            "success": True,
            "content": {
                "title": "Acme Corp - Technology Solutions",
                "html": """
                <html>
                <head><title>Acme Corp - Technology Solutions</title></head>
                <body>
                    <h1>About Acme Corp</h1>
                    <p>We are a leading technology solutions provider.</p>
                    <div class="team">
                        <h2>Leadership Team</h2>
                        <div>John Smith, CEO</div>
                        <div>Jane Doe, CTO</div>
                    </div>
                    <a href="/contact">Contact Us</a>
                    <a href="/team">Meet the Team</a>
                </body>
                </html>
                """,
                "markdown": "# About Acme Corp\n\nWe are a leading technology solutions provider.\n\n## Leadership Team\nJohn Smith, CEO\nJane Doe, CTO",
                "links": [
                    {"url": "/contact", "text": "Contact Us"},
                    {"url": "/team", "text": "Meet the Team"}
                ]
            }
        }
    
    @pytest.mark.asyncio
    async def test_analyze_company_with_direct_url(self, service, mock_crawl_response):
        """Test company analysis with direct URL."""
        request = CompanyAnalysisRequest(
            company_url="https://acmecorp.com",
            extract_employees=True,
            max_employees=10
        )
        
        with patch('app.services.company_analysis_service.CrawlService') as mock_crawl_service:
            mock_crawl_instance = AsyncMock()
            mock_crawl_service.return_value.__aenter__.return_value = mock_crawl_instance
            mock_crawl_instance.crawl.return_value = MagicMock(**mock_crawl_response)
            
            response = await service.analyze_company(request)
            
            assert response.success
            assert response.company is not None
            assert response.company.domain == "acmecorp.com"
            assert response.website_discovery is not None
            assert response.website_discovery.primary_website == "https://acmecorp.com"
            assert len(response.company.employees) >= 0  # May or may not find employees
    
    @pytest.mark.asyncio
    async def test_analyze_company_with_search(self, service, mock_serp_response, mock_crawl_response):
        """Test company analysis with company name search."""
        request = CompanyAnalysisRequest(
            company_name="Acme Corp",
            extract_employees=True,
            max_employees=10
        )
        
        with patch('app.services.company_analysis_service.SERPService') as mock_serp_service, \
             patch('app.services.company_analysis_service.CrawlService') as mock_crawl_service:
            
            # Mock SERP service
            mock_serp_instance = AsyncMock()
            mock_serp_service.return_value.__aenter__.return_value = mock_serp_instance
            mock_serp_instance.search.return_value = MagicMock(**mock_serp_response)
            
            # Mock Crawl service
            mock_crawl_instance = AsyncMock()
            mock_crawl_service.return_value.__aenter__.return_value = mock_crawl_instance
            mock_crawl_instance.crawl.return_value = MagicMock(**mock_crawl_response)
            
            response = await service.analyze_company(request)
            
            assert response.success
            assert response.company is not None
            assert response.company.name == "Acme Corp"
            assert response.website_discovery is not None
            assert response.website_discovery.primary_website == "https://acmecorp.com"
    
    @pytest.mark.asyncio
    async def test_analyze_company_no_website_found(self, service):
        """Test company analysis when no website is found."""
        request = CompanyAnalysisRequest(
            company_name="NonExistent Company"
        )
        
        with patch('app.services.company_analysis_service.SERPService') as mock_serp_service:
            mock_serp_instance = AsyncMock()
            mock_serp_service.return_value.__aenter__.return_value = mock_serp_instance
            mock_serp_instance.search.return_value = MagicMock(
                success=True,
                results=[]  # No results
            )
            
            response = await service.analyze_company(request)
            
            assert not response.success
            assert "Could not discover company website" in response.error_message
    
    @pytest.mark.asyncio
    async def test_analyze_company_crawl_failure(self, service, mock_serp_response):
        """Test company analysis when website crawling fails."""
        request = CompanyAnalysisRequest(
            company_name="Acme Corp"
        )
        
        with patch('app.services.company_analysis_service.SERPService') as mock_serp_service, \
             patch('app.services.company_analysis_service.CrawlService') as mock_crawl_service:
            
            # Mock SERP service (success)
            mock_serp_instance = AsyncMock()
            mock_serp_service.return_value.__aenter__.return_value = mock_serp_instance
            mock_serp_instance.search.return_value = MagicMock(**mock_serp_response)
            
            # Mock Crawl service (failure)
            mock_crawl_instance = AsyncMock()
            mock_crawl_service.return_value.__aenter__.return_value = mock_crawl_instance
            mock_crawl_instance.crawl.return_value = MagicMock(
                success=False,
                error="Failed to crawl website"
            )
            
            response = await service.analyze_company(request)
            
            assert not response.success
            assert "Failed to crawl website" in response.error_message
    
    def test_extract_description(self, service):
        """Test description extraction."""
        # Test with meta description
        content_with_meta = {
            "html": '<meta name="description" content="We are a technology company">',
            "markdown": "Some other content"
        }
        description = service._extract_description(content_with_meta)
        assert description == "We are a technology company"
        
        # Test with markdown fallback
        content_with_markdown = {
            "html": "<html>No meta</html>",
            "markdown": "We are a technology company.\n\nWe build great software."
        }
        description = service._extract_description(content_with_markdown)
        assert description == "We are a technology company."
    
    def test_find_page_url(self, service):
        """Test page URL finding."""
        content = {
            "html": "<html><body></body></html>",
            "links": [
                {"url": "/contact", "text": "Contact Us"},
                {"url": "/about", "text": "About"},
                {"url": "/team", "text": "Meet the Team"},
                {"url": "/careers", "text": "Careers"}
            ]
        }
        
        contact_url = service._find_contact_page(content, "https://company.com")
        assert contact_url == "https://company.com/contact"
        
        team_url = service._find_team_page(content, "https://company.com")
        assert team_url == "https://company.com/team"
        
        careers_url = service._find_careers_page(content, "https://company.com")
        assert careers_url == "https://company.com/careers"
    
    def test_extract_technologies(self, service):
        """Test technology extraction."""
        content = {
            "markdown": """
            We use Python, JavaScript, and React for our development.
            Our infrastructure runs on AWS and Docker.
            We also utilize machine learning and AI technologies.
            """
        }
        
        technologies = service._extract_technologies(content)
        
        assert "Python" in technologies
        assert "Javascript" in technologies
        assert "React" in technologies
        assert "Aws" in technologies
        assert "Docker" in technologies
        assert "Machine Learning" in technologies
    
    def test_extract_keywords(self, service):
        """Test keyword extraction."""
        content = {
            "markdown": """
            We are a SaaS platform providing software solutions for enterprise clients.
            Our technology enables digital transformation through cloud services.
            """
        }
        
        keywords = service._extract_keywords(content)
        
        assert "Saas" in keywords
        assert "Software" in keywords
        assert "Platform" in keywords
        assert "Technology" in keywords
        assert "Digital" in keywords
        assert "Cloud" in keywords