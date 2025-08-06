"""Health check endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime

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
    """Detailed health check with service dependencies."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Google SERP + Crawl4ai API",
            "components": {
                "api": "healthy",
                "bright_data": "not_configured",  # Will be updated when implemented
                "crawl4ai": "not_configured",     # Will be updated when implemented
                "redis": "not_configured"         # Will be updated when implemented
            }
        }
    )