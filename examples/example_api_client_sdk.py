#!/usr/bin/env python3
"""
Production-Ready Python SDK for Company Information Extraction API

This example demonstrates a complete Python SDK for the Company Information
Extraction API with error handling, retry logic, async support, and
production-ready features.

Usage:
    from example_api_client_sdk import CompanyExtractionSDK
    
    sdk = CompanyExtractionSDK()
    company_data = await sdk.extract_company("OpenAI")
"""

import asyncio
import sys
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import time
import httpx
import backoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExtractionMode(Enum):
    """Supported extraction modes."""
    BASIC = "basic"
    STANDARD = "standard" 
    COMPREHENSIVE = "comprehensive"
    CONTACT_FOCUSED = "contact_focused"
    FINANCIAL_FOCUSED = "financial_focused"


class Priority(Enum):
    """Batch processing priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BatchStatus(Enum):
    """Batch processing status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CompanyData:
    """Company information data structure."""
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, Any]] = None
    financial_data: Optional[Dict[str, Any]] = None
    leadership: Optional[Dict[str, Any]] = None
    products_services: Optional[List[str]] = None
    social_media: Optional[Dict[str, str]] = None
    employee_count: Optional[str] = None
    founded_year: Optional[str] = None
    confidence_score: Optional[float] = None
    extraction_metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'CompanyData':
        """Create CompanyData from API response."""
        return cls(
            company_name=data.get("company_name", ""),
            website=data.get("website"),
            industry=data.get("industry"),
            description=data.get("description"),
            headquarters=data.get("headquarters"),
            contact_info=data.get("contact_info"),
            financial_data=data.get("financial_data"),
            leadership=data.get("leadership"),
            products_services=data.get("products_services"),
            social_media=data.get("social_media"),
            employee_count=data.get("employee_count"),
            founded_year=data.get("founded_year"),
            confidence_score=data.get("confidence_score"),
            extraction_metadata=data.get("extraction_metadata")
        )


@dataclass
class BatchResult:
    """Batch processing result."""
    batch_id: str
    status: BatchStatus
    total_companies: int
    completed_companies: int
    failed_companies: int
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_companies == 0:
            return 0.0
        return (self.completed_companies / self.total_companies) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]


@dataclass
class SDKConfig:
    """SDK configuration."""
    base_url: str = "http://localhost:8000"
    timeout: int = 300
    max_retries: int = 3
    retry_backoff_factor: float = 1.0
    api_key: Optional[str] = None
    user_agent: str = "CompanyExtractionSDK/1.0"
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # 1 minute


class CompanyExtractionError(Exception):
    """Base exception for company extraction errors."""
    pass


class APIError(CompanyExtractionError):
    """API-related error."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    pass


class AuthenticationError(APIError):
    """Authentication error."""
    pass


class ValidationError(CompanyExtractionError):
    """Input validation error."""
    pass


class CompanyExtractionSDK:
    """Production-ready Python SDK for Company Information Extraction API."""
    
    def __init__(self, config: Optional[SDKConfig] = None):
        """Initialize the SDK with configuration."""
        self.config = config or SDKConfig()
        self.client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, Any] = {}
        self._rate_limit_tokens = self.config.rate_limit_requests
        self._rate_limit_reset_time = datetime.now() + timedelta(seconds=self.config.rate_limit_window)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup_client()
    
    async def _initialize_client(self):
        """Initialize HTTP client."""
        headers = {
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout),
            headers=headers
        )
    
    async def _cleanup_client(self):
        """Cleanup HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        
        if now >= self._rate_limit_reset_time:
            self._rate_limit_tokens = self.config.rate_limit_requests
            self._rate_limit_reset_time = now + timedelta(seconds=self.config.rate_limit_window)
        
        if self._rate_limit_tokens <= 0:
            raise RateLimitError("Rate limit exceeded. Please wait before making more requests.")
        
        self._rate_limit_tokens -= 1
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key."""
        key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        return key_data
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache."""
        if not self.config.enable_caching:
            return None
        
        cached_data = self._cache.get(cache_key)
        if cached_data:
            cached_time, data = cached_data
            if datetime.now() - cached_time < timedelta(seconds=self.config.cache_ttl):
                return data
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set data in cache."""
        if self.config.enable_caching:
            self._cache[cache_key] = (datetime.now(), data)
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.RequestError, httpx.HTTPStatusError),
        max_tries=3,
        factor=1.0
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        if not self.client:
            raise CompanyExtractionError("SDK not properly initialized. Use async context manager.")
        
        self._check_rate_limit()
        
        # Check cache for GET requests
        if method == "GET" and self.config.enable_caching:
            cache_key = self._get_cache_key(endpoint, params or {})
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {endpoint}")
                return cached_result
        
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params
            )
            
            # Handle different HTTP status codes
            if response.status_code == 200:
                result = response.json()
                
                # Cache successful GET requests
                if method == "GET" and self.config.enable_caching:
                    cache_key = self._get_cache_key(endpoint, params or {})
                    self._set_cache(cache_key, result)
                
                return result
            
            elif response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.")
            
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded by server.")
            
            elif response.status_code >= 500:
                raise APIError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json() if response.content else None
                )
            
            else:
                error_data = response.json() if response.content else {}
                raise APIError(
                    f"API error: {response.status_code} - {error_data.get('error', 'Unknown error')}",
                    status_code=response.status_code,
                    response_data=error_data
                )
        
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        return await self._make_request("GET", "/api/v1/health")
    
    async def extract_company(
        self,
        company_name: str,
        extraction_mode: Union[ExtractionMode, str] = ExtractionMode.STANDARD,
        include_financial_data: bool = True,
        include_contact_info: bool = True,
        max_retries: Optional[int] = None,
        timeout_override: Optional[int] = None
    ) -> CompanyData:
        """
        Extract company information.
        
        Args:
            company_name: Name of the company to extract
            extraction_mode: Extraction mode (basic, standard, comprehensive, etc.)
            include_financial_data: Whether to include financial information
            include_contact_info: Whether to include contact information
            max_retries: Override default retry count
            timeout_override: Override default timeout
            
        Returns:
            CompanyData object with extracted information
            
        Raises:
            ValidationError: Invalid input parameters
            APIError: API request failed
        """
        if not company_name or not company_name.strip():
            raise ValidationError("Company name cannot be empty")
        
        # Convert enum to string if needed
        if isinstance(extraction_mode, ExtractionMode):
            extraction_mode = extraction_mode.value
        
        request_data = {
            "company_name": company_name.strip(),
            "extraction_mode": extraction_mode,
            "include_financial_data": include_financial_data,
            "include_contact_info": include_contact_info
        }
        
        if max_retries is not None:
            request_data["max_retries"] = max_retries
        
        if timeout_override is not None:
            request_data["timeout"] = timeout_override
        
        response = await self._make_request("POST", "/api/v1/company/extract", data=request_data)
        
        if not response.get("success", False):
            error_msg = response.get("error", "Unknown error")
            raise APIError(f"Company extraction failed: {error_msg}")
        
        return CompanyData.from_api_response(response.get("data", {}))
    
    async def submit_batch(
        self,
        company_names: List[str],
        extraction_mode: Union[ExtractionMode, str] = ExtractionMode.STANDARD,
        priority: Union[Priority, str] = Priority.NORMAL,
        include_financial_data: bool = True,
        include_contact_info: bool = True,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit batch extraction request.
        
        Args:
            company_names: List of company names to extract
            extraction_mode: Extraction mode for all companies
            priority: Processing priority
            include_financial_data: Whether to include financial information
            include_contact_info: Whether to include contact information
            webhook_url: Optional webhook URL for completion notification
            metadata: Optional metadata to attach to the batch
            
        Returns:
            Batch ID string
            
        Raises:
            ValidationError: Invalid input parameters
            APIError: API request failed
        """
        if not company_names:
            raise ValidationError("Company names list cannot be empty")
        
        if len(company_names) > 100:  # Assuming 100 is the limit
            raise ValidationError("Too many companies in batch (max 100)")
        
        # Convert enums to strings if needed
        if isinstance(extraction_mode, ExtractionMode):
            extraction_mode = extraction_mode.value
        
        if isinstance(priority, Priority):
            priority = priority.value
        
        # Clean up company names
        cleaned_names = [name.strip() for name in company_names if name.strip()]
        
        request_data = {
            "company_names": cleaned_names,
            "extraction_mode": extraction_mode,
            "priority": priority,
            "include_financial_data": include_financial_data,
            "include_contact_info": include_contact_info
        }
        
        if webhook_url:
            request_data["webhook_url"] = webhook_url
        
        if metadata:
            request_data["metadata"] = metadata
        
        response = await self._make_request("POST", "/api/v1/company/batch/submit", data=request_data)
        
        batch_id = response.get("batch_id")
        if not batch_id:
            raise APIError("No batch ID returned from API")
        
        logger.info(f"Submitted batch {batch_id} with {len(cleaned_names)} companies")
        return batch_id
    
    async def get_batch_status(self, batch_id: str) -> BatchResult:
        """
        Get batch processing status.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            BatchResult object with current status
        """
        if not batch_id:
            raise ValidationError("Batch ID cannot be empty")
        
        response = await self._make_request("GET", f"/api/v1/company/batch/{batch_id}/status")
        
        return BatchResult(
            batch_id=batch_id,
            status=BatchStatus(response.get("status", "unknown")),
            total_companies=response.get("total_companies", 0),
            completed_companies=response.get("completed_companies", 0),
            failed_companies=response.get("failed_companies", 0),
            metadata=response.get("metadata"),
            created_at=self._parse_datetime(response.get("created_at")),
            completed_at=self._parse_datetime(response.get("completed_at"))
        )
    
    async def get_batch_results(self, batch_id: str) -> BatchResult:
        """
        Get batch processing results.
        
        Args:
            batch_id: Batch ID to get results for
            
        Returns:
            BatchResult object with full results
        """
        if not batch_id:
            raise ValidationError("Batch ID cannot be empty")
        
        response = await self._make_request("GET", f"/api/v1/company/batch/{batch_id}/results")
        
        return BatchResult(
            batch_id=batch_id,
            status=BatchStatus(response.get("status", "unknown")),
            total_companies=response.get("total_companies", 0),
            completed_companies=response.get("completed_companies", 0),
            failed_companies=response.get("failed_companies", 0),
            results=response.get("results", []),
            metadata=response.get("metadata"),
            created_at=self._parse_datetime(response.get("created_at")),
            completed_at=self._parse_datetime(response.get("completed_at"))
        )
    
    async def wait_for_batch_completion(
        self,
        batch_id: str,
        polling_interval: int = 10,
        max_wait_time: int = 3600,
        progress_callback: Optional[Callable[[BatchResult], None]] = None
    ) -> BatchResult:
        """
        Wait for batch processing to complete.
        
        Args:
            batch_id: Batch ID to wait for
            polling_interval: Seconds between status checks
            max_wait_time: Maximum time to wait in seconds
            progress_callback: Optional callback for progress updates
            
        Returns:
            Final BatchResult
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            batch_result = await self.get_batch_status(batch_id)
            
            if progress_callback:
                progress_callback(batch_result)
            
            if batch_result.is_complete:
                if batch_result.status == BatchStatus.COMPLETED:
                    return await self.get_batch_results(batch_id)
                else:
                    return batch_result
            
            await asyncio.sleep(polling_interval)
        
        raise APIError(f"Batch {batch_id} did not complete within {max_wait_time} seconds")
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel batch processing.
        
        Args:
            batch_id: Batch ID to cancel
            
        Returns:
            True if successfully cancelled
        """
        if not batch_id:
            raise ValidationError("Batch ID cannot be empty")
        
        response = await self._make_request("DELETE", f"/api/v1/company/batch/{batch_id}")
        return response.get("success", False)
    
    async def get_batch_statistics(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        return await self._make_request("GET", "/api/v1/company/batch/stats")
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string."""
        if not datetime_str:
            return None
        
        try:
            return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    async def bulk_extract_companies(
        self,
        company_names: List[str],
        extraction_mode: Union[ExtractionMode, str] = ExtractionMode.STANDARD,
        batch_size: int = 20,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[CompanyData]:
        """
        Extract multiple companies using optimal batching.
        
        Args:
            company_names: List of company names to extract
            extraction_mode: Extraction mode for all companies
            batch_size: Number of companies per batch
            progress_callback: Optional progress callback (completed, total)
            
        Returns:
            List of CompanyData objects
        """
        if not company_names:
            return []
        
        all_results = []
        total_companies = len(company_names)
        completed_companies = 0
        
        # Process in batches
        for i in range(0, len(company_names), batch_size):
            batch_names = company_names[i:i + batch_size]
            
            try:
                # Submit batch
                batch_id = await self.submit_batch(
                    company_names=batch_names,
                    extraction_mode=extraction_mode,
                    priority=Priority.HIGH
                )
                
                # Wait for completion
                batch_result = await self.wait_for_batch_completion(batch_id)
                
                # Process results
                for result_item in batch_result.results:
                    if result_item.get("success", False):
                        company_data = CompanyData.from_api_response(result_item.get("data", {}))
                        all_results.append(company_data)
                
                completed_companies += len(batch_names)
                
                if progress_callback:
                    progress_callback(completed_companies, total_companies)
                
            except Exception as e:
                logger.error(f"Batch processing failed for companies {batch_names}: {e}")
                # Continue with next batch
                continue
        
        return all_results


# Example usage and demonstrations
async def example_basic_usage():
    """Example: Basic SDK usage."""
    logger.info("Running basic SDK usage example...")
    
    async with CompanyExtractionSDK() as sdk:
        # Health check
        health = await sdk.health_check()
        logger.info(f"API Health: {health}")
        
        # Extract single company
        company_data = await sdk.extract_company(
            company_name="OpenAI",
            extraction_mode=ExtractionMode.STANDARD
        )
        
        logger.info(f"Extracted company: {company_data.company_name}")
        logger.info(f"Industry: {company_data.industry}")
        logger.info(f"Website: {company_data.website}")


async def example_batch_processing():
    """Example: Batch processing with SDK."""
    logger.info("Running batch processing example...")
    
    companies = ["Microsoft", "Google", "Apple", "Amazon"]
    
    async with CompanyExtractionSDK() as sdk:
        # Submit batch
        batch_id = await sdk.submit_batch(
            company_names=companies,
            extraction_mode=ExtractionMode.FINANCIAL_FOCUSED,
            priority=Priority.HIGH
        )
        
        # Wait for completion with progress callback
        def progress_callback(batch_result: BatchResult):
            logger.info(f"Progress: {batch_result.completed_companies}/{batch_result.total_companies} completed")
        
        final_result = await sdk.wait_for_batch_completion(
            batch_id, 
            progress_callback=progress_callback
        )
        
        logger.info(f"Batch completed with {final_result.success_rate:.1f}% success rate")


async def example_bulk_extraction():
    """Example: Bulk extraction with automatic batching."""
    logger.info("Running bulk extraction example...")
    
    companies = [
        "Tesla", "SpaceX", "Neuralink", "Boring Company",
        "Netflix", "Disney", "Warner Bros", "Spotify",
        "Uber", "Lyft", "DoorDash", "Airbnb"
    ]
    
    async with CompanyExtractionSDK() as sdk:
        def progress_callback(completed: int, total: int):
            logger.info(f"Bulk extraction progress: {completed}/{total} ({completed/total*100:.1f}%)")
        
        results = await sdk.bulk_extract_companies(
            company_names=companies,
            extraction_mode=ExtractionMode.COMPREHENSIVE,
            batch_size=6,
            progress_callback=progress_callback
        )
        
        logger.info(f"Successfully extracted data for {len(results)} companies")
        
        for company in results:
            logger.info(f"  - {company.company_name}: {company.industry}")


async def main():
    """Run SDK examples."""
    logger.info("Starting Company Extraction SDK examples...")
    
    try:
        await example_basic_usage()
        await asyncio.sleep(1)
        
        await example_batch_processing()
        await asyncio.sleep(1)
        
        await example_bulk_extraction()
        
        logger.info("All SDK examples completed successfully!")
        
    except Exception as e:
        logger.error(f"SDK example failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())