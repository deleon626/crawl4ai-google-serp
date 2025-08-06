"""FastAPI application entry point."""

import logging
import uvicorn
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
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
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        """Application startup event."""
        logger.info("Starting Google SERP + Crawl4ai API")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"API documentation available at: http://{settings.host}:{settings.port}/docs")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event."""
        logger.info("Shutting down Google SERP + Crawl4ai API")
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers to the FastAPI application."""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error for {request.url}: {exc.errors()}")
        
        def make_serializable(obj):
            """Convert any object to JSON serializable format."""
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            else:
                # Convert any other object to string
                return str(obj)
        
        # Convert errors to JSON serializable format
        serializable_errors = make_serializable(exc.errors())
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "message": "Invalid request data",
                "details": serializable_errors,
                "type": "validation_error"
            }
        )
    
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
    
    @app.exception_handler(BrightDataRateLimitError)
    async def bright_data_rate_limit_handler(request: Request, exc: BrightDataRateLimitError):
        """Handle Bright Data rate limit errors."""
        logger.warning(f"Rate limit error for {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests to the search service. Please try again later.",
                "type": "rate_limit_error",
                "retry_after": "60"  # Suggest retry after 60 seconds
            },
            headers={"Retry-After": "60"}
        )
    
    @app.exception_handler(BrightDataTimeoutError)
    async def bright_data_timeout_handler(request: Request, exc: BrightDataTimeoutError):
        """Handle Bright Data timeout errors."""
        logger.error(f"Timeout error for {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=504,
            content={
                "error": "Request timeout",
                "message": "The search request timed out. Please try again with a simpler query.",
                "type": "timeout_error"
            }
        )
    
    @app.exception_handler(BrightDataError)
    async def bright_data_error_handler(request: Request, exc: BrightDataError):
        """Handle general Bright Data API errors."""
        logger.error(f"Bright Data API error for {request.url}: {str(exc)}")
        return JSONResponse(
            status_code=502,
            content={
                "error": "External API error",
                "message": "Error communicating with the search service. Please try again later.",
                "type": "api_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error for {request.url}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
                "type": "server_error"
            }
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