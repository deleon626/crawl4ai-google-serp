#!/usr/bin/env python3
"""
Test script for LinkedIn query generation functionality.
"""

import asyncio
from app.models.serp import SearchRequest, SocialPlatform, LinkedInContentType
from app.services.serp_service import SERPService

async def test_linkedin_queries():
    """Test LinkedIn query generation with different content types."""
    
    print("🔍 Testing LinkedIn Query Generation")
    print("=" * 50)
    
    base_query = "software engineer"
    
    # Test cases for LinkedIn content types
    test_cases = [
        (LinkedInContentType.ALL, "All LinkedIn Content"),
        (LinkedInContentType.PROFILES, "LinkedIn Profiles Only"),
        (LinkedInContentType.COMPANIES, "LinkedIn Companies Only"),
        (LinkedInContentType.POSTS, "LinkedIn Posts Only"),
        (LinkedInContentType.JOBS, "LinkedIn Jobs Only"),
        (LinkedInContentType.ARTICLES, "LinkedIn Articles Only"),
    ]
    
    service = SERPService()
    
    for content_type, description in test_cases:
        print(f"\n📋 {description}")
        print(f"   Content Type: {content_type.value}")
        
        # Create search request
        request = SearchRequest(
            query=base_query,
            social_platform=SocialPlatform.LINKEDIN,
            linkedin_content_type=content_type
        )
        
        # Generate the modified query
        try:
            modified_query = await service._apply_linkedin_filter_logic(request)
            print(f"   Original Query: '{base_query}'")
            print(f"   Modified Query: '{modified_query}'")
            print(f"   🔗 Google Search URL: https://www.google.com/search?q={modified_query.replace(' ', '+')}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n✅ LinkedIn query testing completed!")

async def test_instagram_vs_linkedin():
    """Test platform switching between Instagram and LinkedIn."""
    
    print("\n\n🔄 Testing Platform Switching")
    print("=" * 50)
    
    base_query = "marketing tips"
    service = SERPService()
    
    # Instagram test
    ig_request = SearchRequest(
        query=base_query,
        social_platform=SocialPlatform.INSTAGRAM,
        instagram_content_type="reels"
    )
    
    ig_query = await service._apply_instagram_filter_logic(ig_request)
    print(f"\n📱 Instagram Reels Query:")
    print(f"   '{ig_query}'")
    
    # LinkedIn test
    li_request = SearchRequest(
        query=base_query,
        social_platform=SocialPlatform.LINKEDIN,
        linkedin_content_type="articles"
    )
    
    li_query = await service._apply_linkedin_filter_logic(li_request)
    print(f"\n💼 LinkedIn Articles Query:")
    print(f"   '{li_query}'")
    
    print(f"\n✅ Platform switching test completed!")

if __name__ == "__main__":
    asyncio.run(test_linkedin_queries())
    asyncio.run(test_instagram_vs_linkedin())