"""Unified logging decorator for consistent request/response logging."""

import logging
import time
import functools
from typing import Callable, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class RequestType(Enum):
    """Types of requests that can be automatically detected."""
    SEARCH = "search"
    BATCH = "batch"
    GENERIC = "generic"


def log_operation(operation: str = "operation", request_type: Optional[RequestType] = None):
    """
    Unified logging decorator that auto-detects request types and logs appropriately.
    
    Args:
        operation: Operation name for logging (default: "operation")
        request_type: Force specific request type, or None for auto-detection
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            # Auto-detect or use specified request type
            detected_type = request_type or _detect_request_type(args, kwargs)
            
            # Log start message based on request type
            _log_start_message(operation, detected_type, args, kwargs)
            
            try:
                result = await func(*args, **kwargs)
                
                # Log completion message based on result type
                duration = time.time() - start_time
                _log_completion_message(operation, detected_type, result, duration, args, kwargs)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{operation.capitalize()} failed after {duration:.3f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator


# Backward compatibility aliases
def log_search_operation(func: Callable) -> Callable:
    """Backward compatible search operation decorator."""
    return log_operation("search", RequestType.SEARCH)(func)


def log_batch_operation(func: Callable) -> Callable:
    """Backward compatible batch operation decorator."""
    return log_operation("batch", RequestType.BATCH)(func)


def log_request_response(operation: str = "operation"):
    """Backward compatible generic request/response decorator."""
    return log_operation(operation, RequestType.GENERIC)


def _detect_request_type(args: tuple, kwargs: dict) -> RequestType:
    """Auto-detect request type from function arguments."""
    # Check for batch request (has max_pages)
    for arg in list(args) + list(kwargs.values()):
        if hasattr(arg, 'query') and hasattr(arg, 'max_pages'):
            return RequestType.BATCH
    
    # Check for search request (has query and country but no max_pages)
    for arg in list(args) + list(kwargs.values()):
        if hasattr(arg, 'query') and hasattr(arg, 'country') and not hasattr(arg, 'max_pages'):
            return RequestType.SEARCH
    
    return RequestType.GENERIC


def _find_request_object(args: tuple, kwargs: dict, request_type: RequestType) -> Optional[Any]:
    """Find the request object of the specified type."""
    all_args = list(args) + list(kwargs.values())
    
    for arg in all_args:
        if request_type == RequestType.BATCH:
            if hasattr(arg, 'query') and hasattr(arg, 'max_pages'):
                return arg
        elif request_type == RequestType.SEARCH:
            if hasattr(arg, 'query') and hasattr(arg, 'country') and not hasattr(arg, 'max_pages'):
                return arg
        elif request_type == RequestType.GENERIC:
            if hasattr(arg, 'query') or hasattr(arg, 'url'):
                return arg
    
    return None


def _log_start_message(operation: str, request_type: RequestType, args: tuple, kwargs: dict):
    """Log operation start message based on request type."""
    request_obj = _find_request_object(args, kwargs, request_type)
    
    if request_type == RequestType.SEARCH and request_obj:
        page = getattr(request_obj, 'page', 'N/A')
        logger.info(f"Processing search request for query: '{request_obj.query}' "
                   f"(country: {request_obj.country}, language: {request_obj.language}, page: {page})")
                   
    elif request_type == RequestType.BATCH and request_obj:
        max_pages = getattr(request_obj, 'max_pages', 'N/A')
        start_page = getattr(request_obj, 'start_page', 1)
        end_page = start_page + max_pages - 1 if max_pages != 'N/A' else 'N/A'
        logger.info(f"Processing batch pagination request for query: '{request_obj.query}' "
                   f"(pages {start_page}-{end_page})")
                   
    else:
        # Generic logging
        request_info = _extract_generic_request_info(args, kwargs)
        logger.info(f"Starting {operation}: {request_info}")


def _log_completion_message(operation: str, request_type: RequestType, result: Any, 
                           duration: float, args: tuple, kwargs: dict):
    """Log operation completion message based on request and result type."""
    if request_type == RequestType.SEARCH:
        if hasattr(result, 'results_count'):
            logger.info(f"Search completed successfully in {duration:.3f}s. "
                       f"Found {result.results_count} results")
        else:
            logger.info(f"Search completed in {duration:.3f}s")
            
    elif request_type == RequestType.BATCH:
        if hasattr(result, 'pages_fetched') and hasattr(result, 'total_results'):
            request_obj = _find_request_object(args, kwargs, request_type)
            max_pages = getattr(request_obj, 'max_pages', 'unknown') if request_obj else 'unknown'
            logger.info(f"Batch pagination completed successfully in {duration:.3f}s. "
                       f"Fetched {result.pages_fetched}/{max_pages} pages "
                       f"({result.total_results} total results)")
        else:
            logger.info(f"Batch operation completed in {duration:.3f}s")
            
    else:
        # Generic logging
        response_info = _extract_generic_response_info(result)
        logger.info(f"{operation.capitalize()} completed in {duration:.3f}s: {response_info}")


def _extract_generic_request_info(args: tuple, kwargs: dict) -> str:
    """Extract generic request information for logging."""
    for arg in args:
        if hasattr(arg, 'query'):
            return f"query='{arg.query}'"
        if hasattr(arg, 'url'):
            return f"url={arg.url}"
    
    for key, value in kwargs.items():
        if hasattr(value, 'query'):
            return f"query='{value.query}'"
        if 'request' in key.lower():
            return str(value)
    
    return "request_info_unavailable"


def _extract_generic_response_info(result: Any) -> str:
    """Extract generic response information for logging."""
    if hasattr(result, 'results_count'):
        return f"results_count={result.results_count}"
    if hasattr(result, 'total_results'):
        return f"total_results={result.total_results}"
    if hasattr(result, 'status'):
        return f"status={result.status}"
    
    return "response_info_available"