"""Unified health check endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime

from app.services.serp_service import SERPService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Google SERP + Crawl4ai API"
        }
    )


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check():
    """Detailed health check with actual service dependency testing."""
    
    components = {}
    overall_status = "healthy"
    http_status = status.HTTP_200_OK
    
    # Test API core
    components["api"] = "healthy"
    
    # Test SERP service and Bright Data connectivity
    try:
        async with SERPService() as service:
            # Test service status
            status_info = await service.get_service_status()
            if status_info.get("status") == "operational":
                components["serp_service"] = "operational"
                components["bright_data"] = "configured"
            else:
                components["serp_service"] = "degraded"
                components["bright_data"] = "error"
                overall_status = "degraded"
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        logger.warning(f"SERP service health check failed: {str(e)}")
        components["serp_service"] = "degraded"
        components["bright_data"] = "error"
        overall_status = "degraded"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Check Crawl4ai (placeholder - not implemented)
    components["crawl4ai"] = "not_implemented"
    
    # Check Redis (placeholder - not implemented)  
    components["redis"] = "not_implemented"
    
    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Google SERP + Crawl4ai API",
            "components": components
        }
    )