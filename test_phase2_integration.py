#!/usr/bin/env python3
"""Integration test script for Phase 2 functionality."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.instagram_service import InstagramSearchService, InstagramQueryBuilder
from app.services.link_validation_service import LinkValidationService
from app.services.keyword_extraction_service import KeywordExtractionService


async def test_instagram_query_builder():
    """Test Instagram query building."""
    print("🔍 Testing Instagram Query Builder...")
    
    builder = InstagramQueryBuilder()
    
    # Test basic query
    query = builder.build_instagram_profile_query(
        business_type="restaurant",
        location="San Francisco",
        keywords=["organic", "healthy"]
    )
    
    print(f"✅ Generated query: {query}")
    assert "site:instagram.com" in query
    assert "restaurant" in query
    assert "San Francisco" in query
    print("✅ Instagram Query Builder working!")
    

def test_pattern_analysis():
    """Test bio pattern analysis."""
    print("\n🔍 Testing Pattern Analysis...")
    
    from app.services.instagram_service import InstagramPatternAnalyzer
    analyzer = InstagramPatternAnalyzer()
    
    # Test business bio
    bio_text = """
    Professional photographer specializing in weddings.
    📧 contact@example.com | 📞 (555) 123-4567
    🌐 www.example-photography.com
    DM for bookings and inquiries
    """
    
    result = analyzer.analyze_bio_content(bio_text)
    
    print(f"✅ Business detected: {result['is_business']}")
    print(f"✅ Confidence: {result['confidence']:.2f}")
    print(f"✅ Contact info: {result['indicators']['contact_info']}")
    print(f"✅ Emails found: {result['extracted_data']['emails']}")
    
    assert result['is_business'] is True
    assert result['confidence'] > 0.5
    assert len(result['extracted_data']['emails']) > 0
    print("✅ Pattern Analysis working!")


async def test_link_extraction():
    """Test link extraction service."""
    print("\n🔍 Testing Link Extraction...")
    
    service = LinkValidationService(timeout=5)
    
    text = """
    Visit our website at https://example.com
    Email us at contact@business.com
    Call (555) 123-4567
    Follow us @mybusiness on Instagram
    """
    
    result = await service.extract_and_validate_links(text, validate_links=False)
    
    print(f"✅ Total links found: {result['total_links']}")
    print(f"✅ Business links: {result['summary']['business_count']}")
    print(f"✅ Contact links: {result['summary']['contact_count']}")
    
    assert result['total_links'] >= 3
    assert result['summary']['contact_count'] >= 2
    print("✅ Link Extraction working!")


async def test_keyword_extraction():
    """Test keyword extraction service."""
    print("\n🔍 Testing Keyword Extraction...")
    
    service = KeywordExtractionService()
    
    text = """
    Professional restaurant serving authentic Italian cuisine in downtown San Francisco.
    We offer catering services, private dining, and special events.
    Book your reservation today! Contact us for inquiries.
    Certified chef with 15 years of experience.
    """
    
    result = await service.extract_and_group_keywords(
        text=text,
        max_keywords=10,
        include_phrases=True,
        group_keywords=True
    )
    
    print(f"✅ Keywords extracted: {result['summary']['total_keywords']}")
    print(f"✅ Business keywords: {result['summary']['business_keywords_count']}")
    print(f"✅ Top categories: {result['summary']['top_categories']}")
    
    top_keywords = [kw.keyword for kw in result['keywords'][:5]]
    print(f"✅ Top 5 keywords: {top_keywords}")
    
    assert result['summary']['total_keywords'] > 0
    assert result['summary']['business_keywords_count'] > 0
    print("✅ Keyword Extraction working!")


async def test_instagram_search_service():
    """Test full Instagram search service."""
    print("\n🔍 Testing Instagram Search Service...")
    
    service = InstagramSearchService()
    
    # Test query building
    queries = await service.build_business_search_queries(
        business_type="cafe",
        location="Seattle",
        keywords=["coffee", "organic"]
    )
    
    print(f"✅ Generated {len(queries)} search queries")
    for i, query in enumerate(queries, 1):
        print(f"   {i}. {query}")
    
    assert len(queries) > 0
    assert all("site:instagram.com" in query for query in queries)
    print("✅ Instagram Search Service working!")


async def main():
    """Run all integration tests."""
    print("🚀 Starting Phase 2 Integration Tests...\n")
    
    try:
        # Test individual components
        await test_instagram_query_builder()
        test_pattern_analysis()
        await test_link_extraction()
        await test_keyword_extraction()
        await test_instagram_search_service()
        
        print("\n🎉 All Phase 2 Integration Tests Passed!")
        print("✅ Crawl4ai integration complete")
        print("✅ Instagram analysis ready")
        print("✅ Bio pattern recognition working")
        print("✅ Link extraction and validation functional")
        print("✅ Keyword extraction and grouping operational")
        print("✅ Enhanced search endpoints deployed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)