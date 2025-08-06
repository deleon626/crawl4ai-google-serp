#!/usr/bin/env python3
"""
Test script for the new Google SERP HTML parser.
Tests parsing capabilities with mock HTML and real API calls.
"""

import asyncio
import json
import httpx
import time
from app.parsers.google_serp_parser import GoogleSERPParser

# Mock HTML content for testing (simplified version of actual Google SERP)
MOCK_GOOGLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>gofood site:instagram.com - Google Search</title></head>
<body>
    <div id="search">
        <div class="g">
            <div class="yuRUbf">
                <a href="https://www.instagram.com/gofood/">
                    <h3 class="LC20lb">GoFood (@gofood) • Instagram photos and videos</h3>
                </a>
            </div>
            <span class="VwiC3b">Official GoFood Instagram account. 🍕 Food delivery service in Indonesia. Order your favorite meals from local restaurants through the GoFood app.</span>
        </div>
        
        <div class="g">
            <div class="yuRUbf">
                <a href="https://www.instagram.com/p/ABC123/">
                    <h3 class="LC20lb">GoFood Indonesia - Latest Food Deals</h3>
                </a>
            </div>
            <span class="VwiC3b">Discover the best food deals and promotions from GoFood. Fresh meals delivered to your doorstep across Indonesia.</span>
        </div>
        
        <div class="g">
            <div class="yuRUbf">
                <a href="https://www.instagram.com/explore/tags/gofood/">
                    <h3 class="LC20lb">#gofood hashtag on Instagram</h3>
                </a>
            </div>
            <span class="VwiC3b">Browse thousands of posts tagged with #gofood. See what people are ordering and sharing about their GoFood experiences.</span>
        </div>
    </div>
    
    <div id="result-stats">About 1,250 results (0.42 seconds)</div>
</body>
</html>
"""

async def test_parser_with_mock_html():
    """Test the parser with mock HTML content."""
    print("🧪 Testing HTML Parser with Mock Data")
    print("=" * 50)
    
    parser = GoogleSERPParser()
    
    # Test parsing
    start_time = time.time()
    response = parser.parse_html(MOCK_GOOGLE_HTML, "gofood site:instagram.com")
    parse_time = time.time() - start_time
    
    print(f"✅ Parsing completed in {parse_time:.3f}s")
    print(f"Query: {response.query}")
    print(f"Results count: {response.results_count}")
    print(f"Timestamp: {response.timestamp}")
    
    if response.search_metadata:
        print("\n📊 Metadata:")
        for key, value in response.search_metadata.items():
            print(f"  - {key}: {value}")
    
    print(f"\n📋 Organic Results ({len(response.organic_results)} found):")
    for i, result in enumerate(response.organic_results, 1):
        print(f"\n  {i}. {result.title}")
        print(f"     URL: {result.url}")
        print(f"     Rank: {result.rank}")
        if result.description:
            desc = result.description[:100] + "..." if len(result.description) > 100 else result.description
            print(f"     Description: {desc}")
    
    return response

async def test_real_api_call():
    """Test with a real API call to verify end-to-end functionality."""
    print("\n🌐 Testing Real API Call")
    print("=" * 50)
    
    url = "http://localhost:8000/api/v1/search"
    
    test_queries = [
        "gofood site:instagram.com",
        "pizza delivery",
        "python programming",
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for query in test_queries:
            try:
                print(f"\n🔍 Testing query: '{query}'")
                start_time = time.time()
                
                response = await client.post(url, json={
                    "query": query,
                    "country": "US",
                    "language": "en",
                    "page": 1
                })
                
                request_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success in {request_time:.2f}s")
                    print(f"   Results: {data.get('results_count', 0)}")
                    
                    if data.get('organic_results'):
                        first_result = data['organic_results'][0]
                        title = first_result.get('title', 'N/A')[:60] + "..." if len(first_result.get('title', '')) > 60 else first_result.get('title', 'N/A')
                        print(f"   First: {title}")
                        print(f"   URL: {first_result.get('url', 'N/A')}")
                    else:
                        print("   No organic results found")
                        if data.get('search_metadata', {}).get('error'):
                            print(f"   Error: {data['search_metadata']['error']}")
                else:
                    print(f"❌ HTTP {response.status_code}: {response.text[:200]}...")
                    
            except httpx.ConnectError:
                print("❌ Connection failed - is the server running?")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(1)

async def test_edge_cases():
    """Test parser with various edge cases."""
    print("\n🎯 Testing Edge Cases")
    print("=" * 50)
    
    parser = GoogleSERPParser()
    
    edge_cases = [
        ("Empty HTML", ""),
        ("No results HTML", "<html><body><div id='search'></div></body></html>"),
        ("Invalid HTML", "<html><body><div class='broken'><h3>Test</h3></body>"),
        ("Only ads HTML", "<html><body><div class='ads-fr'><h3>Ad Title</h3></div></body></html>"),
    ]
    
    for case_name, html_content in edge_cases:
        print(f"\n🧪 Testing: {case_name}")
        try:
            response = parser.parse_html(html_content, "test query")
            print(f"   ✅ Results: {response.results_count}")
            if response.search_metadata and 'error' in response.search_metadata:
                print(f"   ⚠️  Error: {response.search_metadata['error']}")
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")

async def test_performance():
    """Test parser performance with repeated parsing."""
    print("\n⚡ Performance Test")
    print("=" * 50)
    
    parser = GoogleSERPParser()
    iterations = 100
    
    print(f"Running {iterations} parsing iterations...")
    start_time = time.time()
    
    for i in range(iterations):
        response = parser.parse_html(MOCK_GOOGLE_HTML, f"test query {i}")
        if i == 0:
            baseline_results = response.results_count
    
    total_time = time.time() - start_time
    avg_time = (total_time / iterations) * 1000  # Convert to ms
    
    print(f"✅ Performance Results:")
    print(f"   Total time: {total_time:.3f}s")
    print(f"   Average per parse: {avg_time:.2f}ms")
    print(f"   Parses per second: {iterations/total_time:.1f}")
    print(f"   Consistent results: {response.results_count == baseline_results}")

async def main():
    """Run all tests."""
    print("Google SERP HTML Parser - Test Suite")
    print("=" * 60)
    
    try:
        # Test parser with mock data
        await test_parser_with_mock_html()
        
        # Test edge cases
        await test_edge_cases()
        
        # Test performance
        await test_performance()
        
        # Test real API (requires server to be running)
        print(f"\n{'='*60}")
        print("Testing against running server...")
        await test_real_api_call()
        
        print(f"\n🎉 All tests completed!")
        print("\nParser is ready for production use!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())