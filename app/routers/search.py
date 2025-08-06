"""Search API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.models.serp import SearchRequest, SearchResponse
from app.services.serp_service import SERPService
from app.clients.bright_data import (
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


async def get_serp_service() -> SERPService:
    """Dependency injection for SERP service."""
    service = SERPService()
    try:
        yield service
    finally:
        await service.close()


@router.post(
    "/search", 
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Perform Google Search",
    description="Perform a Google search using Bright Data SERP API and return structured results"
)
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
        HTTPException: For various API errors (400, 429, 500, 504)
    """
    try:
        logger.info(f"Processing search request for query: '{search_request.query}' "
                   f"(country: {search_request.country}, language: {search_request.language}, "
                   f"page: {search_request.page})")
        
        # Perform search using SERP service
        search_response = await serp_service.search(search_request)
        
        logger.info(f"Search completed successfully. Found {search_response.results_count} results")
        
        return search_response
        
    except BrightDataRateLimitError as e:
        logger.warning(f"Rate limit exceeded: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "type": "rate_limit_error"
            },
            headers={"Retry-After": "60"}
        )
    
    except BrightDataTimeoutError as e:
        logger.error(f"Request timeout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "Request timeout",
                "message": "The search request timed out. Please try again.",
                "type": "timeout_error"
            }
        )
    
    except BrightDataError as e:
        logger.error(f"Bright Data API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "External API error",
                "message": "Error communicating with search service. Please try again later.",
                "type": "api_error"
            }
        )
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation error",
                "message": str(e),
                "type": "validation_error"
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "type": "server_error"
            }
        )


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
        
        return {
            "status": "operational",
            "service": "search_api",
            "dependencies": {
                "bright_data": "configured",
                "serp_service": "operational"
            }
        }
        
    except Exception as e:
        logger.error(f"Search service status check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "service": "search_api",
                "error": str(e),
                "dependencies": {
                    "bright_data": "unknown",
                    "serp_service": "error"
                }
            }
        )