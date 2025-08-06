#!/usr/bin/env python3
"""
Debug script to trace LinkedIn filter query flow and identify where the filtering breaks.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.models.serp import SearchRequest, SocialPlatform, LinkedInContentType
from app.services.serp_service import SERPService


async def debug_linkedin_filtering():
    """Debug the complete LinkedIn filtering flow."""
    
    print("🔍 LinkedIn Filter Debug Script")
    print("=" * 60)
    
    # Test cases for different LinkedIn filters
    test_cases = [
        {
            "query": "software engineer",
            "linkedin_filter": LinkedInContentType.PROFILES,
            "expected_contains": ["site:linkedin.com", 'inurl:"/in/"', '-inurl:"/company/"'],
            "description": "LinkedIn Profiles Filter"
        },
        {
            "query": "tech companies",
            "linkedin_filter": LinkedInContentType.COMPANIES,
            "expected_contains": ["site:linkedin.com", 'inurl:"/company/"', '-inurl:"/in/"'],
            "description": "LinkedIn Companies Filter"
        },
        {
            "query": "data science",
            "linkedin_filter": LinkedInContentType.JOBS,
            "expected_contains": ["site:linkedin.com", 'inurl:"/jobs/view/"', '-inurl:"/company/"'],
            "description": "LinkedIn Jobs Filter"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['description']}")
        print("-" * 50)
        
        # Create SearchRequest with LinkedIn filtering
        search_request = SearchRequest(
            query=test_case["query"],
            social_platform=SocialPlatform.LINKEDIN,
            linkedin_content_type=test_case["linkedin_filter"],
            country="US",
            language="en",
            page=1,
            results_per_page=10
        )
        
        print(f"📝 Original Query: '{search_request.query}'")
        print(f"🏷️  Platform: {search_request.social_platform}")
        print(f"🔖 LinkedIn Filter: {search_request.linkedin_content_type}")
        
        try:
            # Step 1: Test SERP service filter application
            serp_service = SERPService()
            
            # Access the private method to test just the filtering logic
            modified_request = await serp_service._apply_social_platform_filter(search_request)
            
            print(f"\n✅ SERP Service Output:")
            print(f"   Modified Query: '{modified_request.query}'")
            
            # Validate expected components are present
            missing_components = []
            for expected in test_case["expected_contains"]:
                if expected not in modified_request.query:
                    missing_components.append(expected)
            
            if missing_components:
                print(f"❌ Missing Expected Components: {missing_components}")
            else:
                print(f"✅ All Expected Components Present")
            
            # Step 2: Test what would be sent to Bright Data (simulate)
            print(f"\n🌐 Google URL that would be built:")
            
            # Simulate the _build_google_url method from BrightDataClient
            from urllib.parse import quote
            base_url = "https://www.google.com/search"
            params = [
                f"q={quote(modified_request.query)}",
                f"gl={modified_request.country.lower()}",
                f"hl={modified_request.language}",
                f"start={max(0, (modified_request.page - 1) * modified_request.results_per_page)}",
                f"num={modified_request.results_per_page}"
            ]
            google_url = f"{base_url}?{'&'.join(params)}"
            print(f"   URL: {google_url}")
            
            # Step 3: Verify URL contains LinkedIn filters
            if "site%3Alinkedin.com" in google_url or "site:linkedin.com" in google_url:
                print("✅ LinkedIn site filter found in URL")
            else:
                print("❌ LinkedIn site filter NOT found in URL!")
            
            # Step 4: Test with actual SERP service (but don't make real API call)
            print(f"\n🔧 SERP Service Status Check:")
            try:
                service_status = await serp_service.get_service_status()
                print(f"   Status: {service_status}")
            except Exception as e:
                print(f"   Service Error: {str(e)}")
            
        except Exception as e:
            print(f"❌ Error in test case: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🏁 Debug Script Complete!")


async def test_actual_api_call():
    """Test with actual API call to see what happens."""
    
    print(f"\n\n🌐 Testing Actual API Call")
    print("=" * 60)
    
    # Create a simple LinkedIn profiles search
    search_request = SearchRequest(
        query="python developer",
        social_platform=SocialPlatform.LINKEDIN,
        linkedin_content_type=LinkedInContentType.PROFILES,
        country="US",
        language="en",
        page=1,
        results_per_page=5
    )
    
    print(f"📝 Test Query: '{search_request.query}'")
    print(f"🏷️  Platform: {search_request.social_platform}")
    print(f"🔖 Filter: {search_request.linkedin_content_type}")
    
    try:
        # Use the SERPService as async context manager
        async with SERPService() as serp_service:
            print(f"\n🔄 Making actual search request...")
            
            # This will make a real API call
            response = await serp_service.search(search_request)
            
            print(f"\n📊 Response Summary:")
            print(f"   Query: {response.query}")
            print(f"   Results Count: {response.results_count}")
            print(f"   Timestamp: {response.timestamp}")
            
            if response.search_metadata:
                metadata = response.search_metadata
                print(f"   Original Query: {metadata.get('original_query', 'N/A')}")
                print(f"   Modified Query: {metadata.get('modified_query', 'N/A')}")
                print(f"   Social Platform: {metadata.get('social_platform', 'N/A')}")
                print(f"   LinkedIn Filter: {metadata.get('linkedin_content_type', 'N/A')}")
            
            # Check if results are actually from LinkedIn
            print(f"\n🔍 URL Analysis:")
            linkedin_count = 0
            other_count = 0
            
            for result in response.organic_results[:5]:  # Check first 5 results
                url_str = str(result.url)
                if "linkedin.com" in url_str:
                    linkedin_count += 1
                    print(f"   ✅ LinkedIn: {url_str}")
                else:
                    other_count += 1
                    print(f"   ❌ Other: {url_str}")
            
            print(f"\n📈 Results Summary:")
            print(f"   LinkedIn URLs: {linkedin_count}")
            print(f"   Other URLs: {other_count}")
            
            if linkedin_count == 0 and other_count > 0:
                print(f"🚨 PROBLEM CONFIRMED: No LinkedIn results found!")
            elif linkedin_count > 0:
                print(f"✅ LinkedIn filtering appears to be working")
            
    except Exception as e:
        print(f"❌ API Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting LinkedIn Filter Debug...")
    asyncio.run(debug_linkedin_filtering())
    
    # Ask user if they want to test with actual API call
    try:
        test_api = input("\nDo you want to test with actual API call? (y/N): ").strip().lower()
        if test_api == 'y':
            asyncio.run(test_actual_api_call())
        else:
            print("Skipping actual API test.")
    except KeyboardInterrupt:
        print("\nDebug script interrupted by user.")