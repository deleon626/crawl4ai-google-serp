"""Search API endpoints with optimized error handling and logging."""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.models.serp import SearchRequest, SearchResponse, BatchPaginationResponse
from app.services.serp_service import SERPService
from app.services.batch_pagination_service import BatchPaginationService
from app.routers.base import BaseHandler, create_service_status_response, create_error_status_response
from app.utils.logging_decorators import log_search_operation
from app.clients.bright_data import (
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])
handler = BaseHandler(router)

# Exception handling is done at the app level in main.py
# No need to add handlers to router - they're handled by the FastAPI app instance

# Use base handler dependencies
get_serp_service = handler.get_serp_service
get_batch_pagination_service = handler.get_batch_pagination_service


@router.post(
    "/search", 
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Google Search",
    description="Perform Google search with support for both single-page and multi-page requests. Use max_pages parameter to enable multi-page mode."
)
async def unified_search(
    search_request: SearchRequest,
    serp_service: SERPService = Depends(get_serp_service),
    batch_service: BatchPaginationService = Depends(get_batch_pagination_service)
) -> SearchResponse:
    """
    Unified search endpoint that handles both single-page and multi-page requests.
    
    Single-page mode (default):
    - Use page parameter for pagination
    - Returns standard SearchResponse with pagination metadata
    
    Multi-page mode:
    - Set max_pages > 1 to enable batch processing
    - Returns SearchResponse with additional multi-page fields populated
    - Supports start_page parameter to control starting point
    
    Args:
        search_request: Unified search request with optional multi-page parameters
        serp_service: Injected SERP service dependency (for single-page requests)
        batch_service: Injected batch pagination service dependency (for multi-page requests)
        
    Returns:
        SearchResponse: Unified response supporting both single and multi-page results
        
    Raises:
        HTTPException: For various API errors (handled by centralized exception handlers)
    """
    # Determine request type based on max_pages parameter
    if search_request.is_multi_page_request():
        # Multi-page request - use batch service
        logger.info(f"Processing multi-page search request: max_pages={search_request.max_pages}")
        
        # Convert unified request to batch parameters for the batch service
        batch_response = await batch_service.fetch_batch_pages(search_request)
        
        # Convert BatchPaginationResponse to unified SearchResponse
        unified_response = SearchResponse(
            query=batch_response.query,
            results_count=batch_response.total_results,
            organic_results=batch_response.merged_results,
            
            # Multi-page specific fields
            pages_fetched=batch_response.pages_fetched,
            pages=batch_response.pages,
            merged_results=batch_response.merged_results,
            merged_metadata=batch_response.merged_metadata,
            pagination_summary=batch_response.pagination_summary,
            
            # Common fields
            timestamp=batch_response.timestamp,
            search_metadata={
                "request_type": "multi_page",
                "max_pages": search_request.max_pages,
                "start_page": search_request.get_effective_start_page(),
                "processing_mode": "batch"
            }
        )
        
        return unified_response
    
    else:
        # Single-page request - use standard SERP service
        logger.info(f"Processing single-page search request: page={search_request.page}")
        
        # Apply logging decorator manually for single-page requests
        @log_search_operation
        async def execute_single_search():
            return await serp_service.search(search_request)
        
        single_response = await execute_single_search()
        
        # Ensure search_metadata includes request type
        if single_response.search_metadata is None:
            single_response.search_metadata = {}
        
        single_response.search_metadata.update({
            "request_type": "single_page",
            "processing_mode": "standard"
        })
        
        return single_response


@router.get(
    "/search/status",
    status_code=status.HTTP_200_OK,
    summary="Check Search API Status",
    description="Check the health and availability of the search API and its dependencies"
)
async def search_status():
    """Check search API status and dependencies."""
    try:
        # Try to initialize service to check if it's working
        serp_service = SERPService()
        
        return {
            "service": "search_api",
            "status": "healthy", 
            "dependencies": {
                "bright_data": "available",
                "parser": "available"
            }
        }
    except Exception as e:
        logger.error(f"Search service health check failed: {str(e)}")
        
        # Return degraded status
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": "search_api",
                "status": "degraded",
                "error": str(e),
                "dependencies": {
                    "bright_data": "unknown",
                    "parser": "unknown"
                }
            }
        )


