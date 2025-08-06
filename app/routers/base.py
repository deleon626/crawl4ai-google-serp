"""Base router utilities for common patterns."""

import logging
from typing import Dict, Any
from fastapi import APIRouter

from app.services.serp_service import SERPService
from app.services.batch_pagination_service import BatchPaginationService

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base handler class with common patterns."""
    
    def __init__(self, router: APIRouter):
        self.router = router
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @staticmethod
    async def get_serp_service() -> SERPService:
        """Dependency injection for SERP service."""
        service = SERPService()
        try:
            yield service
        finally:
            await service.close()
    
    @staticmethod
    async def get_batch_pagination_service() -> BatchPaginationService:
        """Dependency injection for batch pagination service."""
        async with BatchPaginationService() as service:
            yield service



def create_service_status_response(service_name: str, dependencies: Dict[str, str]) -> Dict[str, Any]:
    """Create standardized service status response."""
    return {
        "status": "operational",
        "service": service_name,
        "dependencies": dependencies
    }


def create_error_status_response(service_name: str, error: str) -> Dict[str, Any]:
    """Create standardized error status response."""
    return {
        "status": "degraded", 
        "service": service_name,
        "error": error,
        "dependencies": {
            "bright_data": "unknown",
            "serp_service": "error"
        }
    }