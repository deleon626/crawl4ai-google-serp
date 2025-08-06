#!/usr/bin/env python3
"""
Direct test of the API without the web server to verify parsing works.
"""

import asyncio
import json
from app.clients.bright_data import BrightDataClient
from app.models.serp import SearchRequest

async def test_direct_api():
    """Test the API components directly."""

    print("🧪 Direct API Test - Bypassing Web Server")
    print("=" * 60)

    # Test queries
    test_queries = [
        "claude desktop",
        "pizza delivery",
        "claude code"
    ]

    client = BrightDataClient()

    try:
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            print("-" * 40)

            # Create search request
            request = SearchRequest(
                query=query,
                country="US",
                language="en",
                page=1
            )

            # Perform search
            try:
                response = await client.search(request)

                print(f"✅ Results found: {response.results_count}")
                print(f"📊 Content length: {response.search_metadata.get('content_length', 'N/A')}")

                # Show first few results
                for i, result in enumerate(response.organic_results[:3], 1):
                    print(f"\n  {i}. {result.title}")
                    print(f"     URL: {result.url}")
                    if result.description:
                        desc = result.description[:100] + "..." if len(result.description) > 100 else result.description
                        print(f"     Description: {desc}")

                if response.results_count == 0:
                    print("   ℹ️  Possible reasons:")
                    print("     - Query has genuinely no results")
                    print("     - Google serving different content")
                    print("     - Parser needs further refinement")

                    # Show metadata for debugging
                    if 'error' in response.search_metadata:
                        print(f"     - Parser error: {response.search_metadata['error']}")

            except Exception as e:
                print(f"❌ Error: {str(e)}")

    finally:
        await client.close()
        print(f"\n🎯 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_direct_api())
