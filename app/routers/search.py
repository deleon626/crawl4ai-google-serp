"""Search API endpoints with optimized error handling and logging."""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.models.serp import SearchRequest, SearchResponse, BatchPaginationRequest, BatchPaginationResponse
from app.services.serp_service import SERPService
from app.services.batch_pagination_service import BatchPaginationService
from app.routers.base import BaseHandler, create_service_status_response, create_error_status_response
from app.utils.logging_decorators import log_search_operation, log_batch_operation
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
    summary="Perform Google Search",
    description="Perform a Google search using Bright Data SERP API and return structured results"
)
@log_search_operation
async def search_google(
    search_request: SearchRequest,
    serp_service: SERPService = Depends(get_serp_service)
) -> SearchResponse:
    """
    Perform Google search with the provided parameters.
    
    Args:
        search_request: Search request containing query, country, language, and page parameters
        serp_service: Injected SERP service dependency
        
    Returns:
        SearchResponse: Structured search results with organic results and metadata
        
    Raises:
        HTTPException: For various API errors (handled by centralized exception handlers)
    """
    # Exception handling is now centralized - just focus on business logic
    return await serp_service.search(search_request)


@router.post(
    "/search/pages",
    response_model=BatchPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Pagination Search",
    description="Fetch multiple pages of Google search results in a single request with concurrent processing"
)
@log_batch_operation
async def search_batch_pages(
    batch_request: BatchPaginationRequest,
    batch_service: BatchPaginationService = Depends(get_batch_pagination_service)
) -> BatchPaginationResponse:
    """
    Perform batch pagination search to fetch multiple pages concurrently.
    
    Args:
        batch_request: Batch pagination request with search parameters
        batch_service: Injected batch pagination service dependency
        
    Returns:
        BatchPaginationResponse: Results from all fetched pages with summary metadata
        
    Raises:
        HTTPException: For various API errors (handled by centralized exception handlers)
    """
    # Exception handling is now centralized - just focus on business logic
    return await batch_service.fetch_batch_pages(batch_request)


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


