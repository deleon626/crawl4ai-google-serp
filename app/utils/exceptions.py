"""Centralized exception handling utilities."""

import logging
import uuid
from typing import Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.clients.bright_data import (
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)


# Application-specific exceptions
class AppError(Exception):
    """Base application error"""
    pass


class CompanyAnalysisError(AppError):
    """Company analysis operation failed"""
    pass


class CrawlError(AppError):
    """Crawling operation failed"""
    pass

logger = logging.getLogger(__name__)


def generate_trace_id() -> str:
    """Generate unique trace ID for error tracking."""
    return str(uuid.uuid4())[:8]


def create_error_response(
    error_type: str,
    message: str,
    details: str = None,
    trace_id: str = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    headers: Dict[str, str] = None
) -> HTTPException:
    """Create standardized error response."""
    trace_id = trace_id or generate_trace_id()
    
    error_detail = {
        "error": error_type,
        "message": message,
        "type": error_type.lower().replace(" ", "_"),
        "trace_id": trace_id
    }
    
    if details:
        error_detail["details"] = details
    
    return HTTPException(
        status_code=status_code,
        detail=error_detail,
        headers=headers or {}
    )


async def bright_data_rate_limit_handler(request: Request, exc: BrightDataRateLimitError) -> JSONResponse:
    """Handle BrightData rate limit errors."""
    trace_id = generate_trace_id()
    
    logger.warning(f"Rate limit exceeded [trace_id={trace_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "type": "rate_limit_error",
            "trace_id": trace_id
        },
        headers={"Retry-After": "60"}
    )


async def bright_data_timeout_handler(request: Request, exc: BrightDataTimeoutError) -> JSONResponse:
    """Handle BrightData timeout errors."""
    trace_id = generate_trace_id()
    
    logger.error(f"Request timeout [trace_id={trace_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": "Request timeout",
            "message": "The request timed out. Please try again.",
            "type": "timeout_error",
            "trace_id": trace_id
        }
    )


async def bright_data_error_handler(request: Request, exc: BrightDataError) -> JSONResponse:
    """Handle generic BrightData API errors."""
    trace_id = generate_trace_id()
    
    logger.error(f"Bright Data API error [trace_id={trace_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "External API error",
            "message": "Error communicating with search service. Please try again later.",
            "type": "api_error",
            "trace_id": trace_id
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors."""
    trace_id = generate_trace_id()
    
    logger.error(f"Validation error [trace_id={trace_id}]: {exc.errors()}")
    
    # Convert errors to JSON-serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = {}
        for key, value in error.items():
            if key == 'ctx' and isinstance(value, dict):
                # Handle context dict - convert any non-serializable values to strings
                serializable_error[key] = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v 
                                         for k, v in value.items()}
            else:
                # Convert any non-serializable values to strings
                serializable_error[key] = value if isinstance(value, (str, int, float, bool, list, dict, type(None))) else str(value)
        serializable_errors.append(serializable_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "message": "Request validation failed",
            "type": "validation_error",
            "details": serializable_errors,
            "trace_id": trace_id
        }
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle value errors."""
    trace_id = generate_trace_id()
    
    logger.error(f"Value error [trace_id={trace_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Value error",
            "message": str(exc),
            "type": "value_error",
            "trace_id": trace_id
        }
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    trace_id = generate_trace_id()
    
    logger.error(f"Unexpected error [trace_id={trace_id}]: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "type": "server_error",
            "trace_id": trace_id
        }
    )