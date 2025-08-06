#!/usr/bin/env python3
"""
Example usage of the Bright Data SERP API client.

This script demonstrates how to use the BrightDataClient to perform Google searches.
"""

import asyncio
import logging
from app.clients.bright_data import BrightDataClient, BrightDataError
from app.models.serp import SearchRequest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example usage of the Bright Data SERP API client."""
    
    # Create a search request
    search_request = SearchRequest(
        query="pizza near me",
        country="US",
        language="en",
        page=1
    )
    
    # Use the client with async context manager for proper resource cleanup
    try:
        async with BrightDataClient() as client:
            logger.info(f"Searching for: {search_request.query}")
            
            # Perform the search
            response = await client.search(search_request)
            
            # Display results
            logger.info(f"Found {response.results_count} results")
            for result in response.organic_results:
                logger.info(f"Rank {result.rank}: {result.title}")
                logger.info(f"  URL: {result.url}")
                if result.description:
                    logger.info(f"  Description: {result.description}")
                logger.info("")
            
            # Display metadata
            if response.search_metadata:
                logger.info(f"Search metadata: {response.search_metadata}")
                
    except BrightDataError as e:
        logger.error(f"Bright Data API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


async def modern_api_example():
    """Example using the modern SearchRequest/SearchResponse API."""
    
    try:
        async with BrightDataClient() as client:
            logger.info("Using modern SearchRequest API")
            
            # Create search request
            search_request = SearchRequest(
                query="python programming",
                country="US",
                language="en",
                page=1
            )
            
            # Use modern API
            response = await client.search(search_request)
            
            # Display modern format results
            logger.info(f"Modern format - Query: {response.query}")
            logger.info(f"Total results: {response.results_count}")
            logger.info(f"Timestamp: {response.timestamp}")
            
            for result in response.organic_results:
                logger.info(f"Rank {result.rank}: {result.title}")
                logger.info(f"  URL: {result.url}")
                if result.description:
                    logger.info(f"  Description: {result.description}")
                logger.info("")
                
    except BrightDataError as e:
        logger.error(f"Bright Data API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Run the modern examples
    print("=== Modern API Example ===")
    asyncio.run(main())
    
    print("\n=== Modern SearchRequest API Example ===")
    asyncio.run(modern_api_example())