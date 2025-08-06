"""Logging decorators for consistent request/response logging."""

import logging
import time
import functools
from typing import Callable, Any, Dict
from fastapi import Request

logger = logging.getLogger(__name__)


def log_request_response(operation: str = "operation"):
    """Decorator for logging request/response with timing."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract request info
            request_info = _extract_request_info(args, kwargs)
            start_time = time.time()
            
            logger.info(f"Starting {operation}: {request_info}")
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful response
                duration = time.time() - start_time
                response_info = _extract_response_info(result)
                
                logger.info(f"{operation.capitalize()} completed in {duration:.3f}s: {response_info}")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{operation.capitalize()} failed after {duration:.3f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator


def log_search_operation(func: Callable) -> Callable:
    """Specialized decorator for search operations."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Extract search request
        search_request = _find_search_request(args, kwargs)
        start_time = time.time()
        
        if search_request:
            logger.info(f"Processing search request for query: '{search_request.query}' "
                       f"(country: {search_request.country}, language: {search_request.language}, "
                       f"page: {getattr(search_request, 'page', 'N/A')})")
        
        try:
            result = await func(*args, **kwargs)
            
            # Log search results
            duration = time.time() - start_time
            if hasattr(result, 'results_count'):
                logger.info(f"Search completed successfully in {duration:.3f}s. "
                           f"Found {result.results_count} results")
            elif hasattr(result, 'total_results'):
                logger.info(f"Batch search completed successfully in {duration:.3f}s. "
                           f"Found {result.total_results} total results "
                           f"({result.pages_fetched} pages)")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Search operation failed after {duration:.3f}s: {str(e)}")
            raise
            
    return wrapper


def log_batch_operation(func: Callable) -> Callable:
    """Specialized decorator for batch operations."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Extract batch request
        batch_request = _find_batch_request(args, kwargs)
        start_time = time.time()
        
        if batch_request:
            max_pages = getattr(batch_request, 'max_pages', 'N/A')
            start_page = getattr(batch_request, 'start_page', 1)
            end_page = start_page + max_pages - 1 if max_pages != 'N/A' else 'N/A'
            
            logger.info(f"Processing batch pagination request for query: '{batch_request.query}' "
                       f"(pages {start_page}-{end_page})")
        
        try:
            result = await func(*args, **kwargs)
            
            # Log batch results
            duration = time.time() - start_time
            if hasattr(result, 'pages_fetched') and batch_request:
                logger.info(f"Batch pagination completed successfully in {duration:.3f}s. "
                           f"Fetched {result.pages_fetched}/{batch_request.max_pages} pages "
                           f"({result.total_results} total results)")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Batch operation failed after {duration:.3f}s: {str(e)}")
            raise
            
    return wrapper


def _extract_request_info(args: tuple, kwargs: dict) -> str:
    """Extract request information for logging."""
    # Look for request objects in args/kwargs
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


def _extract_response_info(result: Any) -> str:
    """Extract response information for logging."""
    if hasattr(result, 'results_count'):
        return f"results_count={result.results_count}"
    if hasattr(result, 'total_results'):
        return f"total_results={result.total_results}"
    if hasattr(result, 'status'):
        return f"status={result.status}"
    
    return "response_info_available"


def _find_search_request(args: tuple, kwargs: dict) -> Any:
    """Find search request object in function arguments."""
    # Check args
    for arg in args:
        if hasattr(arg, 'query') and hasattr(arg, 'country') and not hasattr(arg, 'max_pages'):
            return arg
    
    # Check kwargs
    for value in kwargs.values():
        if hasattr(value, 'query') and hasattr(value, 'country') and not hasattr(value, 'max_pages'):
            return value
    
    return None


def _find_batch_request(args: tuple, kwargs: dict) -> Any:
    """Find batch request object in function arguments."""
    # Check args
    for arg in args:
        if hasattr(arg, 'query') and hasattr(arg, 'max_pages'):
            return arg
    
    # Check kwargs
    for value in kwargs.values():
        if hasattr(value, 'query') and hasattr(value, 'max_pages'):
            return value
    
    return None