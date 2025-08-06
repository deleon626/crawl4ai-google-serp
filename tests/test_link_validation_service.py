"""Tests for link validation service."""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.link_validation_service import (
    LinkExtractor,
    LinkValidator,
    LinkValidationService
)


class TestLinkExtractor:
    """Test cases for link extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create link extractor fixture."""
        return LinkExtractor()
    
    def test_extract_links_from_text_basic(self, extractor):
        """Test basic link extraction."""
        text = """
        Visit our website at https://example.com for more info.
        You can also check www.another-site.com or contact us at info@business.com
        Call us at (555) 123-4567 for appointments.
        """
        
        links = extractor.extract_links_from_text(text)
        
        assert len(links) >= 4
        
        # Check for different link types
        link_types = [link.link_type for link in links]
        assert "website" in link_types or "http_url" in link_types
        assert "email" in link_types
        assert "phone" in link_types
    
    def test_extract_links_social_media(self, extractor):
        """Test extraction of social media links."""
        text = """
        Follow us on Instagram @mybusiness
        Check our Facebook: facebook.com/mybusiness
        Twitter: twitter.com/mybusiness
        """
        
        links = extractor.extract_links_from_text(text)
        
        # Should find social media links
        social_links = [link for link in links if link.link_type == "social"]
        assert len(social_links) >= 2
        
        # Check domains are recognized as social
        domains = [link.domain for link in links]
        assert any("facebook.com" in domain for domain in domains)
        assert any("twitter.com" in domain for domain in domains)
    
    def test_extract_links_business_platforms(self, extractor):
        """Test extraction of business platform links."""
        text = """
        Shop our products on Etsy: etsy.com/shop/mybusiness
        Visit our Shopify store: mybusiness.shopify.com
        """
        
        links = extractor.extract_links_from_text(text)
        
        business_links = [link for link in links if link.link_type == "business_platform"]
        assert len(business_links) >= 1
    
    def test_extract_links_empty_text(self, extractor):
        """Test extraction from empty text."""
        links = extractor.extract_links_from_text("")
        assert len(links) == 0
        
        links = extractor.extract_links_from_text(None)
        assert len(links) == 0
    
    def test_business_relevance_assessment(self, extractor):
        """Test business relevance scoring."""
        # Business-relevant link
        business_link = extractor._create_link_info(
            "https://business.com/services", 
            "business.com/services", 
            "http_url"
        )
        assert business_link.is_business_link is True
        assert business_link.confidence > 0.3
        
        # Personal link
        personal_link = extractor._create_link_info(
            "https://personal-blog.com/my-thoughts", 
            "personal-blog.com/my-thoughts", 
            "http_url"
        )
        assert personal_link.confidence < 0.5


class TestLinkValidator:
    """Test cases for link validator."""
    
    @pytest.fixture
    def validator_class(self):
        """Return validator class for testing."""
        return LinkValidator
    
    @pytest.mark.asyncio
    async def test_validate_single_link_success(self, validator_class):
        """Test successful link validation."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.head.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.head.return_value.__aexit__ = AsyncMock(return_value=None)
            
            validator = validator_class(timeout=5)
            validator.session = mock_session
            
            # Create test link
            from app.services.link_validation_service import LinkInfo
            link = LinkInfo(
                url="https://example.com",
                original_text="example.com",
                link_type="website",
                domain="example.com",
                is_business_link=True,
                confidence=0.8
            )
            
            # Validate link
            semaphore = AsyncMock()
            result = await validator._validate_single_link(link, semaphore)
            
            assert result.validation_status == "valid"
            assert result.status_code == 200
            assert result.response_time is not None
    
    @pytest.mark.asyncio
    async def test_validate_single_link_not_found(self, validator_class):
        """Test link validation with 404 response."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Setup mock response with 404
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.head.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.head.return_value.__aexit__ = AsyncMock(return_value=None)
            
            validator = validator_class(timeout=5)
            validator.session = mock_session
            
            # Create test link
            from app.services.link_validation_service import LinkInfo
            link = LinkInfo(
                url="https://example.com/nonexistent",
                original_text="example.com/nonexistent",
                link_type="website",
                domain="example.com",
                is_business_link=True,
                confidence=0.8
            )
            
            # Validate link
            semaphore = AsyncMock()
            result = await validator._validate_single_link(link, semaphore)
            
            assert result.validation_status == "not_found"
            assert result.status_code == 404


class TestLinkValidationService:
    """Test cases for link validation service."""
    
    @pytest.fixture
    def service(self):
        """Create link validation service fixture."""
        return LinkValidationService(timeout=5)
    
    @pytest.mark.asyncio
    async def test_extract_and_validate_links_success(self, service):
        """Test successful link extraction and validation."""
        text = """
        Visit our website at https://example.com
        Email us at contact@business.com
        Call (555) 123-4567 for more info
        """
        
        with patch('app.services.link_validation_service.LinkValidator') as mock_validator_class:
            # Setup mock validator
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.__aenter__ = AsyncMock(return_value=mock_validator)
            mock_validator.__aexit__ = AsyncMock(return_value=None)
            
            # Mock validate_links to return links with validation status
            async def mock_validate_links(links):
                for link in links:
                    if link.link_type in ["email", "phone"]:
                        continue
                    link.validation_status = "valid"
                    link.status_code = 200
                    link.response_time = 0.5
                return links
            
            mock_validator.validate_links = mock_validate_links
            
            # Execute extraction and validation
            result = await service.extract_and_validate_links(text, validate_links=True)
            
            # Assertions
            assert result["total_links"] >= 3
            assert result["summary"]["contact_count"] >= 2  # email + phone
            assert result["summary"]["website_count"] >= 1
            assert result["summary"]["validated_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_extract_links_without_validation(self, service):
        """Test link extraction without validation."""
        text = """
        Check our Instagram @mybusiness
        Website: mybusiness.com
        Email: info@mybusiness.com
        """
        
        result = await service.extract_and_validate_links(text, validate_links=False)
        
        assert result["total_links"] >= 2
        assert result["summary"]["validated_count"] == 0
        assert len(result["all_links"]) > 0
        
        # Check that links are categorized correctly
        assert result["summary"]["contact_count"] >= 1  # email
        assert result["summary"]["website_count"] >= 1  # website
    
    @pytest.mark.asyncio
    async def test_extract_links_empty_text(self, service):
        """Test extraction from empty text."""
        result = await service.extract_and_validate_links("", validate_links=False)
        
        assert result["total_links"] == 0
        assert result["summary"]["business_count"] == 0
        assert len(result["all_links"]) == 0