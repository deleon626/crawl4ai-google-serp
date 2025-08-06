"""Tests for Instagram service."""

import pytest
from app.services.instagram_service import (
    InstagramQueryBuilder, 
    InstagramPatternAnalyzer,
    InstagramSearchService
)


class TestInstagramQueryBuilder:
    """Test cases for Instagram query builder."""
    
    @pytest.fixture
    def builder(self):
        """Create Instagram query builder fixture."""
        return InstagramQueryBuilder()
    
    def test_build_instagram_profile_query_basic(self, builder):
        """Test basic Instagram profile query building."""
        query = builder.build_instagram_profile_query()
        
        assert "site:instagram.com" in query
        assert "contact" in query or "email" in query or "phone" in query
        assert "book" in query or "service" in query
    
    def test_build_instagram_profile_query_with_business_type(self, builder):
        """Test query building with business type."""
        query = builder.build_instagram_profile_query(business_type="restaurant")
        
        assert "site:instagram.com" in query
        assert "restaurant" in query
    
    def test_build_instagram_profile_query_with_location(self, builder):
        """Test query building with location."""
        query = builder.build_instagram_profile_query(location="San Francisco")
        
        assert "site:instagram.com" in query
        assert "San Francisco" in query
    
    def test_build_instagram_profile_query_with_keywords(self, builder):
        """Test query building with keywords."""
        query = builder.build_instagram_profile_query(keywords=["organic", "healthy"])
        
        assert "site:instagram.com" in query
        assert "organic" in query
        assert "healthy" in query
    
    def test_build_bio_business_query(self, builder):
        """Test bio-focused business query building."""
        query = builder.build_bio_business_query(["cafe", "coffee"])
        
        assert "site:instagram.com" in query
        assert "cafe" in query
        assert "coffee" in query
        assert "DM for" in query or "contact" in query
    
    def test_build_location_business_query(self, builder):
        """Test location-focused business query building."""
        query = builder.build_location_business_query("New York", ["near", "area"])
        
        assert "site:instagram.com" in query
        assert "New York" in query
        assert "located" in query or "based" in query
        assert "business" in query or "shop" in query


class TestInstagramPatternAnalyzer:
    """Test cases for Instagram pattern analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create Instagram pattern analyzer fixture."""
        return InstagramPatternAnalyzer()
    
    def test_analyze_bio_content_business_profile(self, analyzer):
        """Test analysis of business profile bio."""
        bio_text = """
        Professional photographer specializing in weddings and portraits.
        📧 contact@example.com
        📞 (555) 123-4567
        🌐 www.example-photography.com
        DM for bookings and inquiries
        """
        
        result = analyzer.analyze_bio_content(bio_text)
        
        assert result["is_business"] is True
        assert result["confidence"] > 0.5
        assert "email" in result["indicators"]["contact_info"]
        assert "phone" in result["indicators"]["contact_info"]
        assert "website" in result["indicators"]["contact_info"]
        assert len(result["extracted_data"]["emails"]) > 0
        assert len(result["extracted_data"]["phones"]) > 0
        assert len(result["extracted_data"]["websites"]) > 0
    
    def test_analyze_bio_content_personal_profile(self, analyzer):
        """Test analysis of personal profile bio."""
        bio_text = """
        Just a regular person sharing my daily life.
        Love hiking, cooking, and spending time with friends.
        Follow my journey!
        """
        
        result = analyzer.analyze_bio_content(bio_text)
        
        assert result["is_business"] is False
        assert result["confidence"] < 0.4
        assert len(result["indicators"]["contact_info"]) == 0
        assert len(result["extracted_data"]["emails"]) == 0
    
    def test_analyze_bio_content_empty(self, analyzer):
        """Test analysis of empty bio content."""
        result = analyzer.analyze_bio_content("")
        
        assert result["is_business"] is False
        assert result["confidence"] == 0.0
    
    def test_extract_business_category_restaurant(self, analyzer):
        """Test business category extraction for restaurant."""
        bio_text = "Best Italian restaurant in downtown. Fresh pasta daily!"
        title = "Mario's Italian Kitchen"
        
        category = analyzer.extract_business_category(bio_text, title)
        
        assert category == "food_beverage"
    
    def test_extract_business_category_salon(self, analyzer):
        """Test business category extraction for beauty salon."""
        bio_text = "Hair salon and spa services. Book your appointment today!"
        title = "Beautiful Hair Salon"
        
        category = analyzer.extract_business_category(bio_text, title)
        
        assert category == "beauty_wellness"
    
    def test_extract_business_category_unknown(self, analyzer):
        """Test business category extraction for unknown business."""
        bio_text = "We do amazing things and help people succeed."
        title = "Amazing Company"
        
        category = analyzer.extract_business_category(bio_text, title)
        
        assert category is None or category == "professional_services"


class TestInstagramSearchService:
    """Test cases for Instagram search service."""
    
    @pytest.fixture
    def service(self):
        """Create Instagram search service fixture."""
        return InstagramSearchService()
    
    @pytest.mark.asyncio
    async def test_build_business_search_queries(self, service):
        """Test building business search queries."""
        queries = await service.build_business_search_queries(
            business_type="cafe",
            location="Seattle",
            keywords=["coffee", "organic"]
        )
        
        assert len(queries) > 0
        assert all("site:instagram.com" in query for query in queries)
        assert any("cafe" in query for query in queries)
        assert any("Seattle" in query for query in queries)
    
    @pytest.mark.asyncio
    async def test_build_business_search_queries_minimal(self, service):
        """Test building queries with minimal parameters."""
        queries = await service.build_business_search_queries()
        
        assert len(queries) > 0
        assert all("site:instagram.com" in query for query in queries)
    
    @pytest.mark.asyncio
    async def test_analyze_instagram_profile(self, service):
        """Test Instagram profile analysis."""
        profile_data = {
            "url": "https://instagram.com/test_business",
            "title": "Test Business | Professional Services",
            "description": """
                Professional consulting services for small businesses.
                📧 info@testbusiness.com
                📞 (555) 987-6543
                🌐 www.testbusiness.com
                DM for consultations and quotes
            """,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        result = await service.analyze_instagram_profile(profile_data)
        
        assert result["profile_url"] == "https://instagram.com/test_business"
        assert result["business_analysis"]["is_business"] is True
        assert result["business_analysis"]["confidence"] > 0.5
        assert result["business_category"] is not None
        assert result["metadata"]["has_bio"] is True
        assert result["metadata"]["has_contact_info"] is True
    
    def test_get_confidence_tier(self, service):
        """Test confidence tier classification."""
        assert service._get_confidence_tier(0.9) == "high"
        assert service._get_confidence_tier(0.6) == "medium"
        assert service._get_confidence_tier(0.4) == "low"
        assert service._get_confidence_tier(0.2) == "very_low"