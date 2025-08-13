"""Resilience patterns for company extraction - retry logic, circuit breakers, and error recovery."""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional, Callable, Type, Union, List, Tuple
from dataclasses import dataclass
from enum import Enum

from app.utils.exceptions import (
    CompanyExtractionError, CompanyNotFoundError, ExtractionTimeoutError,
    InsufficientDataError, CrawlTimeoutError, BrightDataError, 
    BrightDataRateLimitError, BrightDataTimeoutError
)

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures for categorized handling."""
    TRANSIENT = "transient"          # Temporary, likely to succeed on retry
    TIMEOUT = "timeout"              # Timeout-related, try with reduced parameters
    RATE_LIMIT = "rate_limit"        # Rate limiting, need backoff
    DATA_QUALITY = "data_quality"    # Poor data quality, try alternative methods
    NOT_FOUND = "not_found"          # Company not found, try different queries
    PERMANENT = "permanent"          # Unlikely to succeed on retry


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_multiplier: float = 1.0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2  # Successes needed to close from half-open
    

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for protecting external service calls."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """Initialize circuit breaker."""
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        async with self._lock:
            if not self._can_execute():
                raise CompanyExtractionError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    "CIRCUIT_BREAKER_OPEN",
                    {"service": self.name, "state": self.state.value}
                )
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
            
        except Exception as e:
            await self._record_failure()
            raise e
    
    def _can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    async def _record_success(self):
        """Record successful operation."""
        async with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker '{self.name}' moved to CLOSED")
            else:
                self.failure_count = 0
    
    async def _record_failure(self):
        """Record failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if (self.state == CircuitBreakerState.CLOSED and 
                self.failure_count >= self.config.failure_threshold):
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' moved to OPEN after {self.failure_count} failures")
            elif self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' moved back to OPEN")


class FailureClassifier:
    """Classifier for different types of failures."""
    
    @staticmethod
    def classify_exception(exception: Exception) -> FailureType:
        """Classify exception to determine retry strategy."""
        if isinstance(exception, BrightDataRateLimitError):
            return FailureType.RATE_LIMIT
        elif isinstance(exception, (BrightDataTimeoutError, CrawlTimeoutError, ExtractionTimeoutError)):
            return FailureType.TIMEOUT
        elif isinstance(exception, (asyncio.TimeoutError, TimeoutError)):
            return FailureType.TIMEOUT
        elif isinstance(exception, BrightDataError):
            # Check if it's a temporary API issue
            error_msg = str(exception).lower()
            if any(term in error_msg for term in ['timeout', 'temporary', 'unavailable', '5']):
                return FailureType.TRANSIENT
            return FailureType.PERMANENT
        elif isinstance(exception, CompanyNotFoundError):
            return FailureType.NOT_FOUND
        elif isinstance(exception, InsufficientDataError):
            return FailureType.DATA_QUALITY
        elif isinstance(exception, (ConnectionError, OSError)):
            return FailureType.TRANSIENT
        else:
            return FailureType.PERMANENT
    
    @staticmethod
    def is_retryable(failure_type: FailureType) -> bool:
        """Check if failure type should be retried."""
        return failure_type in [
            FailureType.TRANSIENT,
            FailureType.TIMEOUT,
            FailureType.RATE_LIMIT,
            FailureType.DATA_QUALITY
        ]


class RetryStrategy:
    """Advanced retry strategies with failure classification."""
    
    def __init__(self, config: RetryConfig = None):
        """Initialize retry strategy."""
        self.config = config or RetryConfig()
        self.classifier = FailureClassifier()
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with intelligent retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_attempts} for {func.__name__}")
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                failure_type = self.classifier.classify_exception(e)
                
                logger.warning(f"Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)} "
                             f"(classified as: {failure_type.value})")
                
                if attempt == self.config.max_attempts - 1:
                    # Last attempt, re-raise
                    raise e
                
                if not self.classifier.is_retryable(failure_type):
                    logger.info(f"Failure type {failure_type.value} is not retryable, stopping")
                    raise e
                
                # Calculate delay based on failure type
                delay = self._calculate_delay(attempt, failure_type)
                
                logger.info(f"Retrying in {delay:.1f}s (failure type: {failure_type.value})")
                await asyncio.sleep(delay)
        
        # Should not reach here, but handle gracefully
        if last_exception:
            raise last_exception
    
    def _calculate_delay(self, attempt: int, failure_type: FailureType) -> float:
        """Calculate delay based on attempt number and failure type."""
        base_delay = self.config.base_delay
        
        # Adjust base delay based on failure type
        if failure_type == FailureType.RATE_LIMIT:
            base_delay *= 3  # Longer delays for rate limits
        elif failure_type == FailureType.TIMEOUT:
            base_delay *= 0.5  # Shorter delays for timeouts
        
        # Exponential backoff
        delay = base_delay * (self.config.exponential_base ** attempt) * self.config.backoff_multiplier
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(delay, 0.1)  # Minimum 100ms delay


class ErrorRecoveryManager:
    """Manager for error recovery strategies."""
    
    def __init__(self):
        """Initialize recovery manager."""
        self.recovery_strategies = {
            FailureType.TIMEOUT: self._recover_from_timeout,
            FailureType.RATE_LIMIT: self._recover_from_rate_limit,
            FailureType.DATA_QUALITY: self._recover_from_data_quality,
            FailureType.NOT_FOUND: self._recover_from_not_found,
        }
    
    async def attempt_recovery(self, 
                              failure_type: FailureType, 
                              original_params: Dict[str, Any],
                              exception: Exception) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover from failure by modifying parameters.
        
        Args:
            failure_type: Type of failure
            original_params: Original function parameters
            exception: The exception that occurred
            
        Returns:
            Modified parameters for retry, or None if no recovery possible
        """
        recovery_strategy = self.recovery_strategies.get(failure_type)
        if not recovery_strategy:
            logger.debug(f"No recovery strategy for {failure_type.value}")
            return None
        
        try:
            modified_params = await recovery_strategy(original_params, exception)
            logger.info(f"Recovery strategy applied for {failure_type.value}")
            return modified_params
        except Exception as e:
            logger.error(f"Recovery strategy failed for {failure_type.value}: {e}")
            return None
    
    async def _recover_from_timeout(self, params: Dict[str, Any], exception: Exception) -> Dict[str, Any]:
        """Recovery strategy for timeout errors."""
        modified = params.copy()
        
        # Reduce timeout if present
        if 'timeout_seconds' in modified:
            original_timeout = modified['timeout_seconds']
            modified['timeout_seconds'] = max(original_timeout * 0.7, 10)
            logger.debug(f"Reduced timeout from {original_timeout}s to {modified['timeout_seconds']}s")
        
        # Reduce max pages to crawl
        if 'max_pages_to_crawl' in modified:
            original_pages = modified['max_pages_to_crawl']
            modified['max_pages_to_crawl'] = max(original_pages // 2, 1)
            logger.debug(f"Reduced max pages from {original_pages} to {modified['max_pages_to_crawl']}")
        
        # Use simpler extraction mode
        if 'extraction_mode' in modified:
            modified['extraction_mode'] = 'BASIC'
            logger.debug("Switched to BASIC extraction mode")
        
        return modified
    
    async def _recover_from_rate_limit(self, params: Dict[str, Any], exception: Exception) -> Dict[str, Any]:
        """Recovery strategy for rate limit errors."""
        modified = params.copy()
        
        # Reduce concurrent requests
        if 'max_concurrent' in modified:
            modified['max_concurrent'] = max(modified['max_concurrent'] // 2, 1)
            logger.debug(f"Reduced concurrent requests to {modified['max_concurrent']}")
        
        # Add longer delays
        if 'base_delay' in modified:
            modified['base_delay'] = modified['base_delay'] * 2
            logger.debug(f"Increased base delay to {modified['base_delay']}s")
        
        return modified
    
    async def _recover_from_data_quality(self, params: Dict[str, Any], exception: Exception) -> Dict[str, Any]:
        """Recovery strategy for data quality issues."""
        modified = params.copy()
        
        # Try comprehensive mode if not already
        if 'extraction_mode' in modified and modified['extraction_mode'] != 'COMPREHENSIVE':
            modified['extraction_mode'] = 'COMPREHENSIVE'
            logger.debug("Switched to COMPREHENSIVE extraction mode")
        
        # Include additional data sources
        if 'include_social_media' in modified:
            modified['include_social_media'] = True
        if 'include_key_personnel' in modified:
            modified['include_key_personnel'] = True
        
        # Increase page limit for more data
        if 'max_pages_to_crawl' in modified:
            modified['max_pages_to_crawl'] = min(modified['max_pages_to_crawl'] + 2, 10)
        
        return modified
    
    async def _recover_from_not_found(self, params: Dict[str, Any], exception: Exception) -> Dict[str, Any]:
        """Recovery strategy for company not found errors."""
        modified = params.copy()
        
        # Try without domain restriction
        if 'domain' in modified and modified['domain']:
            modified['domain'] = None
            logger.debug("Removed domain restriction for broader search")
        
        # Use more general search terms
        if 'company_name' in modified:
            company_name = modified['company_name']
            # Try variations (remove common business suffixes)
            variations = [
                company_name,
                company_name.replace(' Inc', '').replace(' LLC', '').replace(' Corp', ''),
                company_name.replace(' Company', '').replace(' Co.', '')
            ]
            modified['search_variations'] = variations
        
        return modified


# Circuit breaker instances for different services
serp_circuit_breaker = CircuitBreaker("serp_service")
crawl_circuit_breaker = CircuitBreaker("crawl_service")


# Decorator for resilient operations
def resilient_operation(retry_config: RetryConfig = None, 
                       circuit_breaker: CircuitBreaker = None,
                       enable_recovery: bool = True):
    """
    Decorator for resilient operation execution.
    
    Args:
        retry_config: Retry configuration
        circuit_breaker: Circuit breaker instance
        enable_recovery: Whether to enable error recovery
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            retry_strategy = RetryStrategy(retry_config)
            recovery_manager = ErrorRecoveryManager() if enable_recovery else None
            
            async def execute_operation():
                if circuit_breaker:
                    return await circuit_breaker.call(func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)
            
            # First attempt with original parameters
            try:
                return await retry_strategy.execute_with_retry(execute_operation)
            except Exception as first_exception:
                # If recovery is enabled, try with modified parameters
                if recovery_manager:
                    failure_type = FailureClassifier.classify_exception(first_exception)
                    
                    # Extract parameters for recovery (assume first arg is request object)
                    original_params = {}
                    if args and hasattr(args[0], '__dict__'):
                        original_params = args[0].__dict__.copy()
                    
                    recovery_params = await recovery_manager.attempt_recovery(
                        failure_type, original_params, first_exception
                    )
                    
                    if recovery_params:
                        logger.info("Attempting recovery with modified parameters")
                        # Create new request with modified parameters
                        if args and hasattr(args[0], '__class__'):
                            modified_request = args[0].__class__(**recovery_params)
                            modified_args = (modified_request,) + args[1:]
                            
                            async def execute_recovery():
                                if circuit_breaker:
                                    return await circuit_breaker.call(func, *modified_args, **kwargs)
                                else:
                                    return await func(*modified_args, **kwargs)
                            
                            try:
                                return await retry_strategy.execute_with_retry(execute_recovery)
                            except Exception as recovery_exception:
                                logger.warning(f"Recovery attempt failed: {recovery_exception}")
                
                # Recovery failed or not enabled, re-raise original exception
                raise first_exception
        
        return wrapper
    return decorator


# Convenience functions
async def with_circuit_breaker(circuit_breaker: CircuitBreaker, func: Callable, *args, **kwargs):
    """Execute function with circuit breaker protection."""
    return await circuit_breaker.call(func, *args, **kwargs)


async def with_retry(func: Callable, retry_config: RetryConfig = None, *args, **kwargs):
    """Execute function with retry logic."""
    strategy = RetryStrategy(retry_config)
    return await strategy.execute_with_retry(func, *args, **kwargs)


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get status of all circuit breakers."""
    return {
        "serp_service": {
            "state": serp_circuit_breaker.state.value,
            "failure_count": serp_circuit_breaker.failure_count,
            "success_count": serp_circuit_breaker.success_count
        },
        "crawl_service": {
            "state": crawl_circuit_breaker.state.value,
            "failure_count": crawl_circuit_breaker.failure_count,
            "success_count": crawl_circuit_breaker.success_count
        }
    }