#!/usr/bin/env python3
"""
Test LinkedIn filtering with batch search.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.models.serp import BatchPaginationRequest, SocialPlatform, LinkedInContentType
from app.services.batch_pagination_service import BatchPaginationService


async def test_batch_linkedin():
    """Test LinkedIn filtering with batch search."""
    
    print("📄 Testing LinkedIn Filtering with Batch Search")
    print("=" * 60)
    
    # Create a batch request for LinkedIn profiles
    batch_request = BatchPaginationRequest(
        query="software engineer",
        social_platform=SocialPlatform.LINKEDIN,
        linkedin_content_type=LinkedInContentType.PROFILES,
        country="US",
        language="en",
        max_pages=2,
        results_per_page=5,
        start_page=1
    )
    
    print(f"📝 Test Query: '{batch_request.query}'")
    print(f"🏷️  Platform: {batch_request.social_platform}")
    print(f"🔖 LinkedIn Filter: {batch_request.linkedin_content_type}")
    print(f"📄 Pages: {batch_request.max_pages}")
    print(f"📊 Results per page: {batch_request.results_per_page}")
    
    try:
        # Use the BatchPaginationService
        async with BatchPaginationService() as batch_service:
            print(f"\n🔄 Making batch search request...")
            
            # This will make real API calls
            response = await batch_service.fetch_batch_pages(batch_request)
            
            print(f"\n📊 Batch Response Summary:")
            print(f"   Query: {response.query}")
            print(f"   Total Results: {response.total_results}")
            print(f"   Pages Fetched: {response.pages_fetched}")
            print(f"   Processing Time: {response.pagination_summary.batch_processing_time:.2f}s")
            
            # Check merged results
            print(f"\n🔍 Merged Results Analysis:")
            linkedin_count = 0
            other_count = 0
            
            for i, result in enumerate(response.merged_results[:10], 1):  # Check first 10 results
                url_str = str(result.url)
                if "linkedin.com" in url_str:
                    linkedin_count += 1
                    print(f"   {i}. ✅ LinkedIn: {result.title[:50]}...")
                else:
                    other_count += 1
                    print(f"   {i}. ❌ Other: {result.title[:50]}...")
            
            print(f"\n📈 Results Summary:")
            print(f"   LinkedIn URLs: {linkedin_count}")
            print(f"   Other URLs: {other_count}")
            print(f"   Total Results: {len(response.merged_results)}")
            
            if linkedin_count == 0 and other_count > 0:
                print(f"🚨 PROBLEM: Batch LinkedIn filtering not working!")
            elif linkedin_count > 0:
                print(f"✅ Batch LinkedIn filtering is working!")
            else:
                print(f"⚠️  No results returned")
            
            # Check individual pages
            print(f"\n📄 Page-by-Page Analysis:")
            for page in response.pages:
                linkedin_page_count = sum(1 for result in page.organic_results if "linkedin.com" in str(result.url))
                other_page_count = len(page.organic_results) - linkedin_page_count
                print(f"   Page {page.page_number}: {linkedin_page_count} LinkedIn, {other_page_count} Other")
                
                # Show metadata if available
                if page.search_metadata:
                    metadata = page.search_metadata
                    original_query = metadata.get('original_query', 'N/A')
                    modified_query = metadata.get('modified_query', 'N/A')
                    print(f"      Original: {original_query}")
                    print(f"      Modified: {modified_query[:100]}...")
            
    except Exception as e:
        print(f"❌ Batch API Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_batch_linkedin())