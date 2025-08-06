"""SERP service for handling search operations."""

import logging
import time
from typing import Dict, Any, Optional
from app.clients.bright_data import BrightDataClient, BrightDataError
from app.models.serp import SearchRequest, SearchResponse

# Set up logging
logger = logging.getLogger(__name__)


class SERPService:
    """Service for SERP operations with business logic orchestration."""
    
    def __init__(self):
        """Initialize SERP service."""
        self.bright_data_client = None
        logger.info("SERP service initialized")
    
    async def search(self, search_request: SearchRequest) -> SearchResponse:
        """
        Perform search using Bright Data SERP API with business logic.
        
        Args:
            search_request: Search request parameters
            
        Returns:
            SearchResponse with processed search results
            
        Raises:
            BrightDataError: For API-related errors
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting search for query: '{search_request.query}' "
                       f"(country: {search_request.country}, language: {search_request.language}, "
                       f"page: {search_request.page})")
            
            # Ensure client is initialized
            if not self.bright_data_client:
                raise BrightDataError("BrightDataClient not initialized. Use SERPService as async context manager.")
            
            # Perform search using Bright Data client
            search_response = await self.bright_data_client.search(search_request)
            
            # Add business logic processing
            enhanced_response = await self._enhance_search_response(
                search_response, search_request
            )
            
            # Add search timing metadata
            search_time = time.time() - start_time
            if enhanced_response.search_metadata is None:
                enhanced_response.search_metadata = {}
            
            enhanced_response.search_metadata.update({
                "search_time": round(search_time, 3),
                "service_version": "1.0.0",
                "enhanced_processing": True
            })
            
            logger.info(f"Search completed in {search_time:.3f}s with "
                       f"{enhanced_response.results_count} results")
            
            return enhanced_response
            
        except BrightDataError:
            # Re-raise Bright Data specific errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search service: {str(e)}", exc_info=True)
            raise BrightDataError(f"Search service error: {str(e)}")
    
    async def _enhance_search_response(
        self, 
        response: SearchResponse, 
        request: SearchRequest
    ) -> SearchResponse:
        """
        Enhance search response with additional business logic.
        
        Args:
            response: Original search response
            request: Original search request
            
        Returns:
            Enhanced search response
        """
        try:
            # Add request parameters to metadata
            if response.search_metadata is None:
                response.search_metadata = {}
            
            response.search_metadata.update({
                "request_country": request.country,
                "request_language": request.language,
                "request_page": request.page,
                "processing_enhanced": True
            })
            
            # Validate and clean up results
            validated_results = []
            for result in response.organic_results:
                if self._validate_search_result(result):
                    validated_results.append(result)
                else:
                    logger.warning(f"Invalid search result filtered out: {result.title}")
            
            response.organic_results = validated_results
            response.results_count = len(validated_results)
            
            return response
            
        except Exception as e:
            logger.warning(f"Error enhancing search response: {str(e)}")
            # Return original response if enhancement fails
            return response
    
    def _validate_search_result(self, result) -> bool:
        """
        Validate individual search result.
        
        Args:
            result: SearchResult to validate
            
        Returns:
            True if result is valid, False otherwise
        """
        try:
            # Basic validation
            if not result.title or not result.url:
                return False
            
            # URL validation
            url_str = str(result.url)
            if not url_str.startswith(('http://', 'https://')):
                return False
            
            # Title validation
            if len(result.title.strip()) < 3:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating search result: {str(e)}")
            return False
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and health information.
        
        Returns:
            Service status dictionary
        """
        try:
            # Test client connection (this is a lightweight check)
            status_info = {
                "status": "operational",
                "client_initialized": self.bright_data_client is not None,
                "service_version": "1.0.0"
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service_version": "1.0.0"
            }
    
    async def close(self):
        """Close service resources."""
        try:
            if self.bright_data_client:
                await self.bright_data_client.close()
            logger.info("SERP service closed successfully")
        except Exception as e:
            logger.error(f"Error closing SERP service: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry - initialize heavy resources."""
        self.bright_data_client = BrightDataClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self.close()


# Legacy alias for backward compatibility
SerpService = SERPService