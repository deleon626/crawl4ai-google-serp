"""FastAPI application entry point."""

import logging
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from app.routers import health, search, crawl, company, security
from app.security.rate_limiting import rate_limiter, rate_limit_middleware
from app.security.security import security_manager, security_validation_middleware
from app.compliance.monitoring import compliance_manager, compliance_middleware
from app.monitoring.production import production_monitor, monitoring_middleware
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
    generic_error_handler,
    company_extraction_error_handler,
    company_not_found_handler,
    crawl_timeout_handler,
    insufficient_data_handler,
    CompanyAnalysisError,
    CompanyExtractionError,
    CompanyNotFoundError,
    CrawlTimeoutError,
    InsufficientDataError
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
    logger.info("Starting Google SERP + Crawl4ai API with Enterprise Security")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API documentation available at: http://{settings.host}:{settings.port}/docs")
    
    # Initialize security and monitoring systems
    logger.info("Initializing security systems...")
    await rate_limiter.initialize()
    await compliance_manager.initialize_redis()
    await production_monitor.initialize()
    
    logger.info("✅ All security systems initialized successfully")
    logger.info("🛡️  Enterprise-grade security features active")
    logger.info("📊 Production monitoring and alerting enabled")
    logger.info("📋 GDPR compliance monitoring active")
    
    yield
    
    # Shutdown
    logger.info("Shutting down security and monitoring systems...")
    await rate_limiter.shutdown()
    await production_monitor.shutdown()
    logger.info("Shutting down Google SERP + Crawl4ai API")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware combining all security features."""
    
    async def dispatch(self, request: Request, call_next):
        # 1. Production monitoring (first to capture all metrics)
        start_time = time.time()
        
        try:
            # 2. Security validation
            security_details = await security_validation_middleware(request)
            
            # 3. Rate limiting
            await rate_limit_middleware(request)
            
            # 4. Compliance monitoring
            compliance_details = await compliance_middleware(request)
            
            # Process request
            response = await call_next(request)
            
            # 5. Monitoring metrics
            response_time = (time.time() - start_time) * 1000
            await production_monitor.record_metric(
                "request_response_time",
                response_time,
                production_monitor.MetricType.TIMER,
                {
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "status_code": str(response.status_code)
                },
                "milliseconds"
            )
            
            # Add security headers
            response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
            response.headers["X-Security-Level"] = "enterprise"
            response.headers["X-Compliance-Status"] = "gdpr-compliant"
            
            return response
            
        except HTTPException as e:
            # Record error metrics
            response_time = (time.time() - start_time) * 1000
            await production_monitor.record_metric(
                "request_error_count",
                1,
                production_monitor.MetricType.COUNTER,
                {
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "error_type": "http_exception",
                    "status_code": str(e.status_code)
                }
            )
            raise
        except Exception as e:
            # Record error metrics
            response_time = (time.time() - start_time) * 1000
            await production_monitor.record_metric(
                "request_error_count",
                1,
                production_monitor.MetricType.COUNTER,
                {
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "error_type": type(e).__name__
                }
            )
            raise


def create_app() -> FastAPI:
    """Create and configure FastAPI application with enterprise security."""
    
    app = FastAPI(
        title=f"{settings.api_title} - Enterprise Edition",
        description=f"{settings.api_description}\n\n🛡️ **Enterprise Security Features:**\n- Rate limiting and abuse prevention\n- GDPR compliance monitoring\n- Real-time security threat detection\n- Production monitoring and alerting\n- Robots.txt compliance for respectful crawling",
        version=settings.api_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add security headers middleware (first, applies to all responses)
    app.add_middleware(security_manager.get_security_headers_middleware(), 
                      config=security_manager.config)
    
    # Add comprehensive security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Add CORS middleware (more restrictive for production)
    allowed_origins = ["http://localhost:3000", "http://localhost:8501"] if settings.debug else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        expose_headers=["X-Response-Time", "X-Security-Level", "X-Compliance-Status"]
    )
    
    # Add custom exception handlers
    add_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(crawl.router, prefix="/api/v1", tags=["Crawl"])
    app.include_router(company.router, prefix="/api/v1/company", tags=["Company"])
    app.include_router(security.router, prefix="/api/v1/security", tags=["Security & Compliance"])
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add centralized exception handlers to the FastAPI application."""
    
    # Company-specific exception handler function
    async def company_analysis_error_handler(request: Request, exc: CompanyAnalysisError):
        """Handle company analysis errors."""
        logger.error(f"Company analysis error for {request.url}: {exc}")
        
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "Company Analysis Error",
                "message": "Failed to analyze company information from available sources",
                "type": "company_analysis_error",
                "details": str(exc)
            }
        )
    
    # Register centralized exception handlers (most specific first)
    # Company extraction specific errors
    app.add_exception_handler(CompanyNotFoundError, company_not_found_handler)
    app.add_exception_handler(InsufficientDataError, insufficient_data_handler)
    app.add_exception_handler(CompanyExtractionError, company_extraction_error_handler)
    app.add_exception_handler(CompanyAnalysisError, company_analysis_error_handler)
    
    # Crawling specific errors
    app.add_exception_handler(CrawlTimeoutError, crawl_timeout_handler)
    
    # External service errors
    app.add_exception_handler(BrightDataRateLimitError, bright_data_rate_limit_handler)
    app.add_exception_handler(BrightDataTimeoutError, bright_data_timeout_handler)
    app.add_exception_handler(BrightDataError, bright_data_error_handler)
    
    # Generic application errors
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