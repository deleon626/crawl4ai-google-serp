"""SERP service for handling search operations."""

import logging
import time
from typing import Dict, Any, Optional
from app.clients.bright_data import BrightDataClient, BrightDataError
from app.models.serp import SearchRequest, SearchResponse, SocialPlatform, InstagramContentType, LinkedInContentType
from app.utils.caching import get_cache_service
from app.utils.performance import get_performance_monitor

# Set up logging
logger = logging.getLogger(__name__)


class SERPService:
    """Service for SERP operations with business logic orchestration."""
    
    def __init__(self):
        """Initialize SERP service."""
        self.bright_data_client = None
        self.cache_service = None
        self.performance_monitor = None
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
                       f"page: {search_request.page}, platform: {search_request.social_platform}, "
                       f"ig_filter: {search_request.instagram_content_type}, li_filter: {search_request.linkedin_content_type})")
            
            # Ensure client is initialized
            if not self.bright_data_client:
                raise BrightDataError("BrightDataClient not initialized. Use SERPService as async context manager.")
            
            # Apply social platform filtering to query
            modified_request = await self._apply_social_platform_filter(search_request)
            
            # Check cache first if available
            if self.cache_service:
                cached_result = await self.cache_service.get_serp_results(
                    modified_request.query,
                    modified_request.country,
                    modified_request.language,
                    modified_request.page
                )
                
                if cached_result:
                    logger.info(f"Cache hit for SERP query: '{modified_request.query}'")
                    
                    # Record cache hit metric
                    if self.performance_monitor:
                        await self.performance_monitor.record_metric(
                            "serp_cache_hits", 1.0, "count", 
                            {"query": modified_request.query[:50], "country": modified_request.country}
                        )
                    
                    try:
                        # Convert cached data back to SearchResponse
                        search_response = SearchResponse(**cached_result)
                        
                        # Record processing time for cache hit
                        processing_time = time.time() - start_time
                        if self.performance_monitor:
                            await self.performance_monitor.record_metric(
                                "serp_response_time", processing_time, "seconds",
                                {"cached": "true", "query": modified_request.query[:50]}
                            )
                        
                        return search_response
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse cached SERP data: {e}")
                        # Continue with API call
                
                # Record cache miss metric
                if self.performance_monitor:
                    await self.performance_monitor.record_metric(
                        "serp_cache_misses", 1.0, "count", 
                        {"query": modified_request.query[:50], "country": modified_request.country}
                    )
            
            # Perform search using Bright Data client
            search_response = await self.bright_data_client.search(modified_request)
            
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
                "enhanced_processing": True,
                "social_platform": search_request.social_platform.value,
                "instagram_content_type": search_request.instagram_content_type.value,
                "linkedin_content_type": search_request.linkedin_content_type.value,
                "original_query": search_request.query,
                "modified_query": modified_request.query
            })
            
            logger.info(f"Search completed in {search_time:.3f}s with "
                       f"{enhanced_response.results_count} results")
            
            # Cache successful search results if caching available
            if self.cache_service and enhanced_response.results_count > 0:
                try:
                    await self.cache_service.set_serp_results(
                        modified_request.query,
                        modified_request.country,
                        modified_request.language,
                        enhanced_response,
                        modified_request.page
                    )
                    logger.debug(f"Cached SERP results for query: '{modified_request.query}'")
                except Exception as e:
                    logger.warning(f"Failed to cache SERP results: {e}")
            
            # Record performance metrics
            if self.performance_monitor:
                await self.performance_monitor.record_metric(
                    "serp_response_time", search_time, "seconds",
                    {"cached": "false", "query": modified_request.query[:50], "results": str(enhanced_response.results_count)}
                )
                await self.performance_monitor.record_metric(
                    "serp_results_count", float(enhanced_response.results_count), "count",
                    {"query": modified_request.query[:50]}
                )
            
            return enhanced_response
            
        except BrightDataError:
            # Re-raise Bright Data specific errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search service: {str(e)}", exc_info=True)
            raise BrightDataError(f"Search service error: {str(e)}")
    
    async def _apply_social_platform_filter(self, search_request: SearchRequest) -> SearchRequest:
        """
        Apply social platform filtering to search query.
        
        Args:
            search_request: Original search request
            
        Returns:
            Modified search request with social platform filters applied
        """
        try:
            original_query = search_request.query
            modified_query = original_query
            
            # Apply platform-specific filtering
            if search_request.social_platform == SocialPlatform.INSTAGRAM:
                modified_query = await self._apply_instagram_filter_logic(search_request)
            elif search_request.social_platform == SocialPlatform.LINKEDIN:
                modified_query = await self._apply_linkedin_filter_logic(search_request)
            # For SocialPlatform.NONE, keep original query unchanged
            
            # Create modified request with the new query
            modified_request = search_request.model_copy()
            modified_request.query = modified_query
            
            # Enhanced debug logging for LinkedIn filtering issue
            logger.info(f"FILTER DEBUG - Platform: {search_request.social_platform.value}")
            logger.info(f"FILTER DEBUG - LinkedIn Filter Type: {search_request.linkedin_content_type.value}")
            logger.info(f"FILTER DEBUG - Original Query: '{original_query}'")
            logger.info(f"FILTER DEBUG - Modified Query: '{modified_query}'")
            logger.info(f"FILTER DEBUG - Query Changed: {original_query != modified_query}")
            
            # Original log line
            logger.info(f"Social platform filter applied: {search_request.social_platform.value} -> '{modified_query}'")
            
            return modified_request
            
        except Exception as e:
            logger.warning(f"Error applying social platform filter: {str(e)}")
            # Return original request if filtering fails
            return search_request
    
    async def _apply_instagram_filter_logic(self, search_request: SearchRequest) -> str:
        """Apply Instagram-specific query modifications."""
        original_query = search_request.query
        
        # Apply Instagram content type filters
        if search_request.instagram_content_type == InstagramContentType.REELS:
            return f'{original_query} site:instagram.com inurl:"/reel/" -site:business.instagram.com'
        elif search_request.instagram_content_type == InstagramContentType.POSTS:
            return f'{original_query} site:instagram.com inurl:"/p/" -site:business.instagram.com'
        elif search_request.instagram_content_type == InstagramContentType.ACCOUNTS:
            return f'{original_query} site:instagram.com -inurl:"/reel/" -inurl:"/p/" -inurl:"/tv/" -inurl:"/explore/" -site:business.instagram.com'
        elif search_request.instagram_content_type == InstagramContentType.TV:
            return f'{original_query} site:instagram.com inurl:"/tv/" -site:business.instagram.com'
        elif search_request.instagram_content_type == InstagramContentType.LOCATIONS:
            return f'{original_query} site:instagram.com inurl:"/explore/locations/" -site:business.instagram.com'
        else:  # InstagramContentType.ALL
            return f'{original_query} site:instagram.com -site:business.instagram.com'
    
    async def _apply_linkedin_filter_logic(self, search_request: SearchRequest) -> str:
        """Apply LinkedIn-specific query modifications."""
        original_query = search_request.query
        
        # Apply LinkedIn content type filters
        if search_request.linkedin_content_type == LinkedInContentType.PROFILES:
            return f'{original_query} site:linkedin.com inurl:"/in/" -inurl:"/company/" -inurl:"/jobs/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/"'
        elif search_request.linkedin_content_type == LinkedInContentType.COMPANIES:
            return f'{original_query} site:linkedin.com inurl:"/company/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/" -inurl:"/in/"'
        elif search_request.linkedin_content_type == LinkedInContentType.POSTS:
            return f'{original_query} site:linkedin.com (inurl:"/feed/" OR inurl:"/posts/") -inurl:"/company/" -inurl:"/in/" -inurl:"/jobs/" -inurl:"/pulse/"'
        elif search_request.linkedin_content_type == LinkedInContentType.JOBS:
            return f'{original_query} site:linkedin.com inurl:"/jobs/view/" -inurl:"/company/" -inurl:"/in/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/pulse/"'
        elif search_request.linkedin_content_type == LinkedInContentType.ARTICLES:
            return f'{original_query} site:linkedin.com inurl:"/pulse/" -inurl:"/company/" -inurl:"/in/" -inurl:"/posts/" -inurl:"/feed/" -inurl:"/jobs/"'
        else:  # LinkedInContentType.ALL
            return f'{original_query} site:linkedin.com'
    
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
        
        # Initialize caching and performance monitoring
        try:
            self.cache_service = await get_cache_service()
            self.performance_monitor = await get_performance_monitor()
            logger.debug("SERP service caching and performance monitoring initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize SERP caching/performance monitoring: {e}")
            # Continue without caching/monitoring
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self.close()


# Legacy alias for backward compatibility
SerpService = SERPService