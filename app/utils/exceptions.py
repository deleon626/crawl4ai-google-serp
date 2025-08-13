"""Centralized exception handling utilities."""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, Union, List
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from urllib.parse import urlparse
import re

from app.clients.bright_data import (
    BrightDataError, 
    BrightDataRateLimitError, 
    BrightDataTimeoutError
)


# Application-specific exceptions
class AppError(Exception):
    """Base application error."""
    
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = time.time()


# Crawling errors
class CrawlError(AppError):
    """Base crawling operation error."""
    pass


class CrawlTimeoutError(CrawlError):
    """Crawling operation timed out."""
    pass


class CrawlInsufficientContentError(CrawlError):
    """Crawled content does not meet minimum requirements."""
    pass


# Company extraction errors
class CompanyExtractionError(AppError):
    """Base company information extraction error."""
    pass


class CompanyNotFoundError(CompanyExtractionError):
    """No company information could be found or extracted."""
    
    def __init__(self, company_name: str, message: str = None, context: Dict[str, Any] = None):
        message = message or f"No company information found for '{company_name}'"
        super().__init__(message, "COMPANY_NOT_FOUND", context)
        self.company_name = company_name


class InvalidCompanyDomainError(CompanyExtractionError):
    """Invalid or malformed company domain provided."""
    
    def __init__(self, domain: str, message: str = None, context: Dict[str, Any] = None):
        message = message or f"Invalid domain format: '{domain}'"
        super().__init__(message, "INVALID_DOMAIN", context)
        self.domain = domain


class ExtractionTimeoutError(CompanyExtractionError):
    """Company extraction process exceeded timeout limit."""
    
    def __init__(self, timeout_seconds: int, message: str = None, context: Dict[str, Any] = None):
        message = message or f"Extraction timeout after {timeout_seconds} seconds"
        super().__init__(message, "EXTRACTION_TIMEOUT", context)
        self.timeout_seconds = timeout_seconds


class InsufficientDataError(CompanyExtractionError):
    """Extracted data does not meet confidence or quality thresholds."""
    
    def __init__(self, confidence_score: float = None, threshold: float = None, 
                 message: str = None, context: Dict[str, Any] = None):
        if confidence_score is not None and threshold is not None:
            message = message or f"Data confidence {confidence_score:.2f} below threshold {threshold:.2f}"
        else:
            message = message or "Insufficient data quality for reliable extraction"
        super().__init__(message, "INSUFFICIENT_DATA", context)
        self.confidence_score = confidence_score
        self.threshold = threshold


class CompanyAnalysisError(CompanyExtractionError):
    """Company data analysis and processing error."""
    
    def __init__(self, analysis_type: str = None, message: str = None, context: Dict[str, Any] = None):
        message = message or f"Analysis error in {analysis_type}" if analysis_type else "Company analysis failed"
        super().__init__(message, "ANALYSIS_ERROR", context)
        self.analysis_type = analysis_type


class CompanyValidationError(CompanyExtractionError):
    """Company data validation error."""
    
    def __init__(self, field: str = None, value: Any = None, message: str = None, context: Dict[str, Any] = None):
        if field and value is not None:
            message = message or f"Invalid {field}: {value}"
        else:
            message = message or "Company data validation failed"
        super().__init__(message, "VALIDATION_ERROR", context)
        self.field = field
        self.value = value

logger = logging.getLogger(__name__)


# Retry configuration
class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


# Circuit breaker for external services
class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


def generate_trace_id() -> str:
    """Generate unique trace ID for error tracking."""
    return str(uuid.uuid4())[:8]


# Validation utilities
class ValidationUtils:
    """Utilities for data validation and sanitization."""
    
    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """Validate domain format."""
        if not domain or not isinstance(domain, str):
            return False
        
        # Remove protocol and www if present
        domain = domain.lower().strip()
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        
        # Basic domain regex
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain)) and len(domain) <= 253
    
    @staticmethod
    def normalize_domain(domain: str) -> str:
        """Normalize domain format."""
        if not domain:
            return ""
        
        domain = domain.lower().strip()
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.rstrip('/')
        return domain
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        if not url or not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
        except Exception:
            return False
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = None) -> str:
        """Sanitize and clean text content."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text
    
    @staticmethod
    def calculate_confidence_score(data: Dict[str, Any], required_fields: List[str], 
                                 optional_fields: List[str] = None) -> float:
        """Calculate confidence score based on data completeness."""
        if not data:
            return 0.0
        
        required_score = 0.0
        optional_score = 0.0
        
        # Required fields (70% weight)
        if required_fields:
            required_present = sum(1 for field in required_fields if data.get(field))
            required_score = (required_present / len(required_fields)) * 0.7
        
        # Optional fields (30% weight)
        if optional_fields:
            optional_present = sum(1 for field in optional_fields if data.get(field))
            optional_score = (optional_present / len(optional_fields)) * 0.3
        
        return min(required_score + optional_score, 1.0)
    
    @staticmethod
    def validate_company_name(name: str) -> bool:
        """Validate company name format."""
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        return 2 <= len(name) <= 200 and bool(re.match(r'^[\w\s\-\.,&()]+$', name))


# Retry decorator with exponential backoff
def with_retry(config: RetryConfig = None, retryable_exceptions: tuple = None):
    """Decorator for automatic retry with exponential backoff."""
    config = config or RetryConfig()
    retryable_exceptions = retryable_exceptions or (Exception,)
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt, re-raise
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                                 f"Retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                except Exception as e:
                    # Non-retryable exception
                    raise e
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


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


# New error handlers for company extraction errors
async def company_extraction_error_handler(request: Request, exc: CompanyExtractionError) -> JSONResponse:
    """Handle company extraction errors."""
    trace_id = generate_trace_id()
    
    # Map specific error types to HTTP status codes
    status_code_map = {
        "COMPANY_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "INVALID_DOMAIN": status.HTTP_400_BAD_REQUEST,
        "EXTRACTION_TIMEOUT": status.HTTP_408_REQUEST_TIMEOUT,
        "INSUFFICIENT_DATA": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "ANALYSIS_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.error(f"Company extraction error [trace_id={trace_id}]: {exc.error_code} - {str(exc)}")
    
    # Build error response
    error_response = {
        "error": "Company extraction error",
        "message": str(exc),
        "type": exc.error_code.lower(),
        "trace_id": trace_id,
        "timestamp": exc.timestamp
    }
    
    # Add specific error context
    if hasattr(exc, 'company_name') and exc.company_name:
        error_response["company_name"] = exc.company_name
    if hasattr(exc, 'domain') and exc.domain:
        error_response["domain"] = exc.domain
    if hasattr(exc, 'confidence_score') and exc.confidence_score is not None:
        error_response["confidence_score"] = exc.confidence_score
    if hasattr(exc, 'threshold') and exc.threshold is not None:
        error_response["threshold"] = exc.threshold
    if exc.context:
        error_response["context"] = exc.context
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def company_not_found_handler(request: Request, exc: CompanyNotFoundError) -> JSONResponse:
    """Handle company not found errors."""
    trace_id = generate_trace_id()
    
    logger.warning(f"Company not found [trace_id={trace_id}]: {exc.company_name}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Company not found",
            "message": f"No information could be found for company '{exc.company_name}'",
            "type": "company_not_found",
            "trace_id": trace_id,
            "company_name": exc.company_name,
            "suggestions": [
                "Check the company name spelling",
                "Try providing a company domain",
                "Ensure the company has a web presence"
            ]
        }
    )


async def crawl_timeout_handler(request: Request, exc: CrawlTimeoutError) -> JSONResponse:
    """Handle crawl timeout errors."""
    trace_id = generate_trace_id()
    
    logger.warning(f"Crawl timeout [trace_id={trace_id}]: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={
            "error": "Crawl timeout",
            "message": "Web crawling operation timed out. Please try again.",
            "type": "crawl_timeout",
            "trace_id": trace_id,
            "retry_suggestions": [
                "Try again with a shorter timeout",
                "Check if the target website is responsive",
                "Consider reducing the number of pages to crawl"
            ]
        }
    )


async def insufficient_data_handler(request: Request, exc: InsufficientDataError) -> JSONResponse:
    """Handle insufficient data errors."""
    trace_id = generate_trace_id()
    
    logger.warning(f"Insufficient data [trace_id={trace_id}]: {str(exc)}")
    
    response_content = {
        "error": "Insufficient data quality",
        "message": str(exc),
        "type": "insufficient_data",
        "trace_id": trace_id,
        "recommendations": [
            "Try providing more specific company information",
            "Check if the company has an official website",
            "Consider using a different extraction mode"
        ]
    }
    
    if exc.confidence_score is not None:
        response_content["confidence_score"] = exc.confidence_score
    if exc.threshold is not None:
        response_content["required_threshold"] = exc.threshold
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_content
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


# Error recovery strategies
class ErrorRecoveryStrategy:
    """Strategies for recovering from different types of errors."""
    
    @staticmethod
    async def recover_from_timeout(original_request, timeout_seconds: int, max_retries: int = 2):
        """Recovery strategy for timeout errors."""
        logger.info(f"Attempting timeout recovery with reduced timeout: {timeout_seconds // 2}s")
        # Implementation would retry with reduced parameters
        pass
    
    @staticmethod
    async def recover_from_insufficient_data(company_name: str, original_domain: str = None):
        """Recovery strategy for insufficient data errors."""
        logger.info(f"Attempting data recovery for {company_name} with alternative approaches")
        # Implementation would try alternative extraction methods
        pass
    
    @staticmethod
    async def recover_from_crawl_failure(urls: List[str], failed_url: str):
        """Recovery strategy for crawl failures."""
        logger.info(f"Attempting crawl recovery, skipping failed URL: {failed_url}")
        # Implementation would continue with remaining URLs
        pass


# Quality assessment utilities
class DataQualityAssessment:
    """Utilities for assessing data quality and completeness."""
    
    @staticmethod
    def assess_company_data_quality(data: Dict[str, Any]) -> Dict[str, Union[float, str]]:
        """Assess the quality of extracted company data."""
        if not data:
            return {"quality_score": 0.0, "assessment": "no_data", "issues": ["No data provided"]}
        
        quality_score = 0.0
        issues = []
        
        # Basic information completeness (40% of score)
        basic_fields = ['name', 'description', 'website']
        basic_present = sum(1 for field in basic_fields if data.get(field))
        basic_score = (basic_present / len(basic_fields)) * 0.4
        quality_score += basic_score
        
        if basic_present < len(basic_fields):
            missing = [field for field in basic_fields if not data.get(field)]
            issues.append(f"Missing basic fields: {', '.join(missing)}")
        
        # Contact information completeness (30% of score)
        contact_fields = ['email', 'phone', 'address']
        if data.get('contact'):
            contact_present = sum(1 for field in contact_fields if data['contact'].get(field))
            contact_score = (contact_present / len(contact_fields)) * 0.3
            quality_score += contact_score
            
            if contact_present < len(contact_fields):
                missing_contact = [field for field in contact_fields if not data['contact'].get(field)]
                issues.append(f"Missing contact fields: {', '.join(missing_contact)}")
        else:
            issues.append("No contact information available")
        
        # Additional data richness (30% of score)
        additional_fields = ['industry', 'founded_year', 'employee_count', 'social_media', 'key_personnel']
        additional_present = sum(1 for field in additional_fields if data.get(field))
        additional_score = (additional_present / len(additional_fields)) * 0.3
        quality_score += additional_score
        
        # Determine assessment level
        if quality_score >= 0.8:
            assessment = "high_quality"
        elif quality_score >= 0.6:
            assessment = "good_quality"
        elif quality_score >= 0.4:
            assessment = "moderate_quality"
        else:
            assessment = "low_quality"
        
        return {
            "quality_score": round(quality_score, 2),
            "assessment": assessment,
            "issues": issues,
            "completeness_breakdown": {
                "basic_info": round(basic_score / 0.4, 2) if basic_score > 0 else 0.0,
                "contact_info": round((quality_score - basic_score - additional_score) / 0.3, 2) 
                               if quality_score > basic_score + additional_score else 0.0,
                "additional_data": round(additional_score / 0.3, 2) if additional_score > 0 else 0.0
            }
        }
    
    @staticmethod
    def get_improvement_suggestions(assessment: Dict[str, Any]) -> List[str]:
        """Get suggestions for improving data quality."""
        suggestions = []
        
        if assessment["quality_score"] < 0.6:
            suggestions.extend([
                "Try providing a company domain for better targeting",
                "Use comprehensive extraction mode for more data",
                "Check if the company has an official website"
            ])
        
        if "Missing basic fields" in str(assessment.get("issues", [])):
            suggestions.append("Verify company name spelling and try alternative search terms")
        
        if "Missing contact fields" in str(assessment.get("issues", [])):
            suggestions.append("Enable contact-focused extraction mode for better contact data")
        
        if assessment["completeness_breakdown"]["additional_data"] < 0.5:
            suggestions.append("Include social media and personnel data for richer information")
        
        return suggestions