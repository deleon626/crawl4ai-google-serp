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

# Setup centralized exception handling
from app.utils.exceptions import (
    bright_data_rate_limit_handler,
    bright_data_timeout_handler,
    bright_data_error_handler,
    validation_error_handler,
    generic_error_handler
)

router.add_exception_handler(BrightDataRateLimitError, bright_data_rate_limit_handler)
router.add_exception_handler(BrightDataTimeoutError, bright_data_timeout_handler)
router.add_exception_handler(BrightDataError, bright_data_error_handler)
router.add_exception_handler(ValueError, validation_error_handler)
router.add_exception_handler(Exception, generic_error_handler)

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
    summary="Search Service Status",
    description="Check the status of the search service and external dependencies"
)
async def search_status() -> Dict[str, Any]:
    """
    Get the status of the search service and its dependencies.
    
    Returns:
        Dict containing service status information
    """
    try:
        # Test SERP service initialization
        service = SERPService()
        await service.close()
        
        return create_service_status_response(
            "search_api", 
            {
                "bright_data": "configured",
                "serp_service": "operational"
            }
        )
        
    except Exception as e:
        logger.error(f"Search service status check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=create_error_status_response("search_api", str(e))
        )