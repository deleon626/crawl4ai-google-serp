#!/usr/bin/env python3
"""Debug script to inspect the actual HTML content returned by Bright Data."""

import asyncio
import json
from app.clients.bright_data import BrightDataClient
from app.models.serp import SearchRequest

async def debug_html_content():
    """Inspect actual HTML returned by Bright Data to understand structure."""
    
    client = BrightDataClient()
    
    # Test query
    search_request = SearchRequest(
        query="pizza near me",
        country="US",
        language="en",
        page=1
    )
    
    try:
        # Get raw response data by temporarily modifying the client
        google_url = client._build_google_url(search_request)
        print(f"Google URL: {google_url}")
        
        payload = {
            "zone": client.zone,
            "url": google_url,
            "format": "raw"
        }
        
        response_data = await client._make_request_with_retry(payload)
        
        print(f"\nHTML Content Length: {len(response_data)} characters")
        print(f"First 2000 characters:")
        print("-" * 80)
        print(response_data[:2000])
        print("-" * 80)
        
        # Look for common Google SERP elements
        elements_to_check = [
            "<title>",
            'class="g"',
            'class="LC20lb"',
            'class="yuRUbf"',
            'class="VwiC3b"',
            'id="search"',
            'id="main"',
            '<h3',
            'href="http',
            'data-ved',
        ]
        
        print(f"\nElement presence check:")
        for element in elements_to_check:
            count = response_data.count(element)
            print(f"  {element}: {count} occurrences")
        
        # Save full HTML to file for analysis
        with open('/tmp/google_serp_debug.html', 'w', encoding='utf-8') as f:
            f.write(response_data)
        print(f"\n📁 Full HTML saved to: /tmp/google_serp_debug.html")
        
        # Test parsing with our parser
        print(f"\n🔍 Testing with our parser:")
        parsed_response = client.parser.parse_html(response_data, search_request.query)
        print(f"  Results found: {parsed_response.results_count}")
        print(f"  Metadata: {json.dumps(parsed_response.search_metadata, indent=2)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_html_content())