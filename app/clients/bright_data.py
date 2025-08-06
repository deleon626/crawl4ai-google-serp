"""Bright Data SERP API client."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote
import httpx

from config.settings import settings
from app.models.serp import SearchRequest, SearchResponse, SearchResult
from app.parsers.google_serp_parser import GoogleSERPParser

# Set up logging
logger = logging.getLogger(__name__)


class BrightDataError(Exception):
    """Base exception for Bright Data API errors."""
    pass


class BrightDataRateLimitError(BrightDataError):
    """Exception for rate limit errors."""
    pass


class BrightDataTimeoutError(BrightDataError):
    """Exception for timeout errors."""
    pass


class BrightDataClient:
    """Client for Bright Data SERP API."""
    
    def __init__(self):
        """Initialize Bright Data client."""
        self.api_url = settings.bright_data_api_url
        self.token = settings.bright_data_token
        self.zone = settings.bright_data_zone
        self.timeout = settings.bright_data_timeout
        self.max_retries = settings.bright_data_max_retries
        
        # Initialize HTML parser
        self.parser = GoogleSERPParser()
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "GoogleSERP-Crawl4ai/1.0"
            }
        )
    
    async def search(self, search_request: SearchRequest) -> SearchResponse:
        """
        Perform Google search using Bright Data SERP API.
        
        Args:
            search_request: SearchRequest model with query parameters
            
        Returns:
            SearchResponse model with search results
            
        Raises:
            BrightDataError: For API-related errors
            BrightDataRateLimitError: For rate limiting errors
            BrightDataTimeoutError: For timeout errors
        """
        logger.info(f"Performing search for query: {search_request.query}")
        
        # Build Google search URL with parameters
        google_url = self._build_google_url(search_request)
        
        # Prepare API request payload
        payload = {
            "zone": self.zone,
            "url": google_url,
            "format": "raw"
        }
        
        # Perform request with retry logic
        response_data = await self._make_request_with_retry(payload)
        
        # Parse response using our new HTML parser with pagination metadata
        return self.parser.parse_html(
            response_data, 
            search_request.query,
            current_page=search_request.page,
            results_per_page=search_request.results_per_page
        )
    
    def _build_google_url(self, search_request: SearchRequest) -> str:
        """
        Build Google search URL with parameters.
        
        Args:
            search_request: SearchRequest model
            
        Returns:
            Formatted Google search URL
        """
        base_url = "https://www.google.com/search"
        params = [
            f"q={quote(search_request.query)}",
            f"gl={search_request.country.lower()}",
            f"hl={search_request.language}",
            f"start={max(0, (search_request.page - 1) * search_request.results_per_page)}",
            f"num={search_request.results_per_page}"
        ]
        
        return f"{base_url}?{'&'.join(params)}"
    
    async def _make_request_with_retry(self, payload: Dict[str, Any]) -> str:
        """
        Make API request with exponential backoff retry logic.
        
        Args:
            payload: Request payload
            
        Returns:
            Raw response content
            
        Raises:
            BrightDataError: For API-related errors
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1} of {self.max_retries + 1}")
                
                response = await self.client.post(self.api_url, json=payload)
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    logger.info("Request successful")
                    return response.text
                
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded"
                    logger.warning(error_msg)
                    raise BrightDataRateLimitError(error_msg)
                
                elif response.status_code == 401:
                    error_msg = "Authentication failed - invalid token"
                    logger.error(error_msg)
                    raise BrightDataError(error_msg)
                
                elif response.status_code == 400:
                    error_msg = f"Bad request: {response.text}"
                    logger.error(error_msg)
                    raise BrightDataError(error_msg)
                
                else:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise BrightDataError(error_msg)
                
            except httpx.TimeoutException as e:
                error_msg = f"Request timeout: {str(e)}"
                logger.warning(error_msg)
                last_exception = BrightDataTimeoutError(error_msg)
                
            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                logger.warning(error_msg)
                last_exception = BrightDataError(error_msg)
            
            except (BrightDataRateLimitError, BrightDataError):
                # Don't retry authentication or rate limit errors
                raise
            
            # Exponential backoff for retries
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        # If all retries failed, raise the last exception
        if last_exception:
            raise last_exception
        else:
            raise BrightDataError("Request failed after all retries")
    
    
    async def close(self):
        """Close the HTTP client."""
        logger.info("Closing Bright Data client")
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Legacy method for backward compatibility
    async def search_google(
        self, 
        query: str, 
        country: str = "US", 
        language: str = "en",
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        
        Args:
            query: Search query string
            country: Country code for search
            language: Language code for search
            page: Page number for pagination
            
        Returns:
            Dict containing search results
        """
        search_request = SearchRequest(
            query=query,
            country=country,
            language=language,
            page=page
        )
        
        response = await self.search(search_request)
        
        # Convert to legacy format
        return {
            "query": response.query,
            "results": [
                {
                    "title": result.title,
                    "url": str(result.url),
                    "snippet": result.description,
                    "position": result.rank
                }
                for result in response.organic_results
            ],
            "total_results": response.results_count,
            "search_time": 0.0,  # Not available in new format
            "status": "success"
        }