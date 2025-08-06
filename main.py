"""FastAPI application entry point."""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from app.routers import health, search
from app.clients.bright_data import (
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)
from app.utils.exceptions import (
    bright_data_rate_limit_handler,
    bright_data_timeout_handler,
    bright_data_error_handler,
    validation_error_handler,
    value_error_handler,
    generic_error_handler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Google SERP + Crawl4ai API")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API documentation available at: http://{settings.host}:{settings.port}/docs")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Google SERP + Crawl4ai API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom exception handlers
    add_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add centralized exception handlers to the FastAPI application."""
    
    # Register centralized exception handlers
    app.add_exception_handler(BrightDataRateLimitError, bright_data_rate_limit_handler)
    app.add_exception_handler(BrightDataTimeoutError, bright_data_timeout_handler)
    app.add_exception_handler(BrightDataError, bright_data_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
    
    # Keep HTTP exception handler for now (may consolidate later)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP {exc.status_code} error for {request.url}: {exc.detail}")
        
        # If detail is already a structured dict, use it directly
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=exc.headers
            )
        
        # Otherwise, create a standard response
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "type": "http_error"
            },
            headers=exc.headers
        )


# Create app instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )