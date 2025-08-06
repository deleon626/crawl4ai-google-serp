#!/usr/bin/env python3
"""
Example usage script for the Google SERP API.

This script demonstrates how to use the search API endpoint with different 
search scenarios, error handling, and response processing.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
import httpx
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SearchAPIClient:
    """Client for the Google SERP API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
        self.search_endpoint = f"{self.base_url}/api/v1/search"
        self.status_endpoint = f"{self.base_url}/api/v1/search/status"
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )
    
    async def search(
        self, 
        query: str, 
        country: str = "US", 
        language: str = "en", 
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Perform a search request.
        
        Args:
            query: Search query string
            country: Country code (ISO 3166-1 alpha-2)
            language: Language code (ISO 639-1)  
            page: Page number for pagination
            
        Returns:
            Search response dictionary
            
        Raises:
            httpx.HTTPError: For HTTP-related errors
        """
        payload = {
            "query": query,
            "country": country,
            "language": language,
            "page": page
        }
        
        logger.info(f"Searching for: '{query}' (country: {country}, language: {language}, page: {page})")
        
        start_time = time.time()
        
        try:
            response = await self.client.post(self.search_endpoint, json=payload)
            response.raise_for_status()
            
            search_time = time.time() - start_time
            logger.info(f"Search completed in {search_time:.2f}s")
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error: {e.response.text}")
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except json.JSONDecodeError:
                pass
            raise
        
        except httpx.TimeoutException:
            logger.error("Request timed out")
            raise
        
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the search service status.
        
        Returns:
            Status response dictionary
        """
        try:
            response = await self.client.get(self.status_endpoint)
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"Error getting status: {str(e)}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def print_search_results(response: Dict[str, Any]):
    """
    Pretty print search results.
    
    Args:
        response: Search response dictionary
    """
    print(f"\n{'='*80}")
    print(f"Search Results for: '{response['query']}'")
    print(f"Results found: {response['results_count']}")
    print(f"Search timestamp: {response['timestamp']}")
    
    if response.get('search_metadata'):
        metadata = response['search_metadata']
        if 'search_time' in metadata:
            print(f"Search time: {metadata['search_time']:.3f}s")
    
    print(f"{'='*80}")
    
    if not response['organic_results']:
        print("No organic results found.")
        return
    
    for i, result in enumerate(response['organic_results'], 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Rank: {result['rank']}")
        
        if result.get('description'):
            # Wrap long descriptions
            description = result['description']
            if len(description) > 100:
                description = description[:97] + "..."
            print(f"   Description: {description}")
    
    print(f"\n{'='*80}")


async def example_basic_search(client: SearchAPIClient):
    """Example of basic search functionality."""
    print("\n🔍 Example 1: Basic Search")
    print("-" * 50)
    
    try:
        response = await client.search("artificial intelligence")
        print_search_results(response)
        
    except Exception as e:
        logger.error(f"Basic search failed: {str(e)}")


async def example_international_search(client: SearchAPIClient):
    """Example of international search with different countries and languages."""
    print("\n🌍 Example 2: International Search")
    print("-" * 50)
    
    search_configs = [
        {"query": "pizza", "country": "IT", "language": "it"},
        {"query": "sushi", "country": "JP", "language": "ja"}, 
        {"query": "croissant", "country": "FR", "language": "fr"},
        {"query": "fish and chips", "country": "GB", "language": "en"}
    ]
    
    for config in search_configs:
        try:
            print(f"\nSearching in {config['country']} ({config['language']}):")
            response = await client.search(**config)
            print(f"Found {response['results_count']} results for '{config['query']}'")
            
            # Show first result only for brevity
            if response['organic_results']:
                result = response['organic_results'][0]
                print(f"Top result: {result['title']}")
                print(f"URL: {result['url']}")
            
        except Exception as e:
            logger.error(f"International search failed for {config['country']}: {str(e)}")


async def example_pagination(client: SearchAPIClient):
    """Example of pagination through search results."""
    print("\n📄 Example 3: Pagination")
    print("-" * 50)
    
    query = "python programming tutorial"
    
    try:
        for page in [1, 2, 3]:
            print(f"\n--- Page {page} ---")
            response = await client.search(query, page=page)
            
            print(f"Results {(page-1)*10 + 1}-{min(page*10, response['results_count'])} "
                  f"for '{query}'")
            
            if response['organic_results']:
                # Show first result from each page
                result = response['organic_results'][0]
                print(f"First result: {result['title']}")
                print(f"Rank: {result['rank']}")
            
            # Small delay between requests
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Pagination example failed: {str(e)}")


async def example_error_handling(client: SearchAPIClient):
    """Example of error handling scenarios."""
    print("\n⚠️ Example 4: Error Handling")
    print("-" * 50)
    
    # Test invalid requests
    invalid_requests = [
        {"query": "", "description": "Empty query"},
        {"query": "test", "country": "usa", "description": "Invalid country code"},
        {"query": "test", "language": "EN", "description": "Invalid language code"},
        {"query": "test", "page": 0, "description": "Invalid page number"},
    ]
    
    for req in invalid_requests:
        try:
            print(f"\nTesting: {req['description']}")
            
            # Remove description from request
            search_params = {k: v for k, v in req.items() if k != 'description'}
            response = await client.search(**search_params)
            
            print(f"Unexpected success: {response['results_count']} results")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                print(f"✓ Validation error caught as expected (HTTP 422)")
                try:
                    error_detail = e.response.json()
                    print(f"  Error type: {error_detail.get('type', 'unknown')}")
                    print(f"  Message: {error_detail.get('message', 'No message')}")
                except json.JSONDecodeError:
                    pass
            else:
                print(f"✗ Unexpected HTTP error: {e.response.status_code}")
        
        except Exception as e:
            print(f"✗ Unexpected error: {str(e)}")


async def example_service_status(client: SearchAPIClient):
    """Example of checking service status."""
    print("\n🏥 Example 5: Service Status Check")
    print("-" * 50)
    
    try:
        status = await client.get_status()
        
        print(f"Service: {status.get('service', 'unknown')}")
        print(f"Status: {status.get('status', 'unknown')}")
        
        if 'dependencies' in status:
            print("\nDependencies:")
            for dep, dep_status in status['dependencies'].items():
                status_icon = "✅" if dep_status == "operational" else "⚠️"
                print(f"  {status_icon} {dep}: {dep_status}")
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")


async def example_batch_searches(client: SearchAPIClient):
    """Example of performing multiple searches efficiently."""
    print("\n🚀 Example 6: Batch Searches")
    print("-" * 50)
    
    queries = [
        "machine learning",
        "web development", 
        "data science",
        "cybersecurity",
        "cloud computing"
    ]
    
    print(f"Performing {len(queries)} searches concurrently...")
    start_time = time.time()
    
    try:
        # Perform searches concurrently
        tasks = [client.search(query) for query in queries]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        print(f"\nBatch completed in {total_time:.2f}s")
        print(f"Average time per search: {total_time/len(queries):.2f}s")
        
        # Process results
        for query, response in zip(queries, responses):
            if isinstance(response, Exception):
                print(f"❌ '{query}': {str(response)}")
            else:
                print(f"✅ '{query}': {response['results_count']} results")
        
    except Exception as e:
        logger.error(f"Batch search failed: {str(e)}")


async def main():
    """Main example runner."""
    print("Google SERP API - Example Usage")
    print("=" * 80)
    
    # Check if server is running
    async with SearchAPIClient() as client:
        try:
            # Test connection
            await client.get_status()
            print("✅ Successfully connected to API server")
            
        except httpx.ConnectError:
            print("❌ Could not connect to API server.")
            print("   Please make sure the server is running on http://localhost:8000")
            print("   Run: python main.py")
            return
        
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return
        
        # Run examples
        examples = [
            example_service_status,
            example_basic_search,
            example_international_search, 
            example_pagination,
            example_batch_searches,
            example_error_handling,
        ]
        
        for example_func in examples:
            try:
                await example_func(client)
                await asyncio.sleep(1)  # Small delay between examples
                
            except KeyboardInterrupt:
                print("\n\n⏹️ Examples interrupted by user")
                break
            
            except Exception as e:
                logger.error(f"Example {example_func.__name__} failed: {str(e)}")
                continue
        
        print("\n🎉 All examples completed!")
        print("\nNext steps:")
        print("- Try the interactive API docs at: http://localhost:8000/docs")
        print("- Run the test suite: python -m pytest tests/")
        print("- Check out the API health: http://localhost:8000/api/v1/health")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Example script failed: {str(e)}")
        exit(1)