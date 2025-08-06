"""
Batch pagination service for Google SERP API.

This service handles efficient batch pagination requests, allowing users to fetch
multiple pages of search results in a single request with concurrent processing.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from app.models.serp import (
    SearchRequest,
    SearchResult,
    BatchPaginationRequest,
    BatchPaginationResponse,
    BatchPaginationSummary,
    PageResult,
    MergedResultsMetadata
)
from app.clients.bright_data import BrightDataClient, BrightDataError
from app.utils.pagination import PaginationHelper

# Set up logging
logger = logging.getLogger(__name__)


class BatchPaginationService:
    """
    Service for handling batch pagination requests with concurrent processing.
    
    Provides efficient methods for fetching multiple pages of search results
    simultaneously while managing rate limits and errors gracefully.
    """
    
    def __init__(self, max_concurrent_requests: int = 5, delay_between_requests: float = 0.5):
        """
        Initialize the batch pagination service.
        
        Args:
            max_concurrent_requests: Maximum number of concurrent requests
            delay_between_requests: Delay between requests to manage rate limits
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.delay_between_requests = delay_between_requests
        self.pagination_helper = PaginationHelper()
        self.bright_data_client: Optional[BrightDataClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.bright_data_client = BrightDataClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.bright_data_client:
            await self.bright_data_client.close()
    
    async def fetch_batch_pages(self, request: BatchPaginationRequest) -> BatchPaginationResponse:
        """
        Fetch multiple pages of search results in a batch request.
        
        Args:
            request: BatchPaginationRequest with search parameters
            
        Returns:
            BatchPaginationResponse with results from all fetched pages
            
        Raises:
            ValueError: For invalid request parameters
            BrightDataError: For API-related errors
        """
        logger.info(f"Starting batch pagination for query: '{request.query}' "
                   f"(pages {request.start_page} to {request.start_page + request.max_pages - 1})")
        
        # Validate request parameters
        self._validate_batch_request(request)
        
        start_time = time.time()
        pages_fetched = 0
        page_results: List[PageResult] = []
        total_results = 0
        total_results_estimate = None
        
        # Create individual search requests for each page
        search_requests = self._create_search_requests(request)
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Fetch pages concurrently with rate limiting
        tasks = [
            self._fetch_single_page_with_semaphore(semaphore, search_req, page_num)
            for page_num, search_req in enumerate(search_requests, start=request.start_page)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        for i, result in enumerate(results):
            page_number = request.start_page + i
            
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch page {page_number}: {str(result)}")
                # Create empty page result for failed requests
                page_result = PageResult(
                    page_number=page_number,
                    results_count=0,
                    organic_results=[],
                    search_metadata={'error': str(result)}
                )
            else:
                # Successful result
                search_response = result
                pages_fetched += 1
                total_results += search_response.results_count
                
                # Use the first successful page's total estimate for all
                if total_results_estimate is None and search_response.pagination:
                    total_results_estimate = search_response.pagination.total_results_estimate
                
                page_result = PageResult(
                    page_number=page_number,
                    results_count=search_response.results_count,
                    organic_results=search_response.organic_results,
                    pagination=search_response.pagination,
                    search_metadata=search_response.search_metadata
                )
            
            page_results.append(page_result)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create batch pagination summary
        pagination_summary = BatchPaginationSummary(
            total_results_estimate=total_results_estimate,
            results_per_page=request.results_per_page,
            pages_requested=request.max_pages,
            pages_fetched=pages_fetched,
            start_page=request.start_page,
            end_page=request.start_page + request.max_pages - 1,
            batch_processing_time=processing_time
        )
        
        # Merge results from all pages
        merged_results, merged_metadata = self._merge_page_results(page_results)
        
        # Create response
        response = BatchPaginationResponse(
            query=request.query,
            total_results=total_results,
            pages_fetched=pages_fetched,
            pagination_summary=pagination_summary,
            pages=page_results,
            merged_results=merged_results,
            merged_metadata=merged_metadata
        )
        
        logger.info(f"Batch pagination completed: {pages_fetched}/{request.max_pages} pages fetched "
                   f"in {processing_time:.2f}s ({total_results} total results, "
                   f"{len(merged_results)} merged)")
        
        return response
    
    async def _fetch_single_page_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore, 
        search_request: SearchRequest,
        page_number: int
    ):
        """
        Fetch a single page with semaphore rate limiting.
        
        Args:
            semaphore: Semaphore for controlling concurrency
            search_request: SearchRequest for this page
            page_number: Page number for logging
            
        Returns:
            SearchResponse for this page
        """
        async with semaphore:
            try:
                logger.debug(f"Fetching page {page_number}...")
                
                # Add delay to manage rate limits
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)
                
                # Fetch the page using SERP service to ensure Instagram filtering is applied
                if not self.bright_data_client:
                    raise RuntimeError("BrightDataClient not initialized")
                
                # Import here to avoid circular imports
                from app.services.serp_service import SERPService
                
                # Create temporary SERP service with the same client
                temp_serp_service = SERPService()
                temp_serp_service.bright_data_client = self.bright_data_client
                
                search_response = await temp_serp_service.search(search_request)
                logger.debug(f"Successfully fetched page {page_number} "
                           f"({search_response.results_count} results)")
                
                return search_response
                
            except Exception as e:
                logger.warning(f"Failed to fetch page {page_number}: {str(e)}")
                raise
    
    def _create_search_requests(self, batch_request: BatchPaginationRequest) -> List[SearchRequest]:
        """
        Create individual SearchRequest objects for each page.
        
        Args:
            batch_request: BatchPaginationRequest
            
        Returns:
            List of SearchRequest objects
        """
        search_requests = []
        
        for page_offset in range(batch_request.max_pages):
            page_number = batch_request.start_page + page_offset
            
            search_request = SearchRequest(
                query=batch_request.query,
                country=batch_request.country,
                language=batch_request.language,
                page=page_number,
                results_per_page=batch_request.results_per_page,
                instagram_content_type=batch_request.instagram_content_type
            )
            
            search_requests.append(search_request)
        
        return search_requests
    
    def _merge_page_results(self, pages: List[PageResult]) -> tuple[List[SearchResult], MergedResultsMetadata]:
        """
        Merge organic results from all pages into a single list with continuous ranking.
        
        Args:
            pages: List of PageResult objects to merge
            
        Returns:
            Tuple of (merged_results, merge_metadata)
        """
        merge_start_time = time.time()
        merged_results: List[SearchResult] = []
        continuous_rank = 1
        pages_with_results = []
        
        # Sort pages by page number to ensure correct order
        sorted_pages = sorted(pages, key=lambda p: p.page_number)
        
        # Extract and re-rank all organic results
        for page in sorted_pages:
            if page.organic_results:
                pages_with_results.append(page.page_number)
                
                for result in page.organic_results:
                    # Create new SearchResult with continuous ranking
                    merged_result = SearchResult(
                        rank=continuous_rank,
                        title=result.title,
                        url=result.url,
                        description=result.description
                    )
                    merged_results.append(merged_result)
                    continuous_rank += 1
        
        merge_processing_time = time.time() - merge_start_time
        
        # Create metadata
        metadata = MergedResultsMetadata(
            total_merged_results=len(merged_results),
            continuous_rank_start=1 if merged_results else 0,
            continuous_rank_end=continuous_rank - 1,
            pages_included=pages_with_results,
            merge_processing_time=merge_processing_time
        )
        
        logger.debug(f"Merged {len(merged_results)} results from {len(pages_with_results)} pages "
                    f"in {merge_processing_time:.4f}s")
        
        return merged_results, metadata

    def _validate_batch_request(self, request: BatchPaginationRequest) -> None:
        """
        Validate batch pagination request parameters.
        
        Args:
            request: BatchPaginationRequest to validate
            
        Raises:
            ValueError: For invalid parameters
        """
        # Validate individual parameters
        is_valid, error_msg = self.pagination_helper.validate_pagination_params(
            page=request.start_page,
            results_per_page=request.results_per_page,
            max_page=100,
            max_results_per_page=100
        )
        
        if not is_valid:
            raise ValueError(f"Invalid pagination parameters: {error_msg}")
        
        # Validate batch-specific parameters
        if request.max_pages > 10:
            raise ValueError("Cannot fetch more than 10 pages in a single batch request")
        
        if request.start_page + request.max_pages - 1 > 100:
            raise ValueError("End page cannot exceed page 100")
        
        # Check for reasonable limits
        total_results_requested = request.max_pages * request.results_per_page
        if total_results_requested > 1000:
            raise ValueError(f"Cannot request more than 1000 total results "
                           f"(requested: {total_results_requested})")


class BatchPaginationError(Exception):
    """Exception raised for batch pagination errors."""
    pass


# Factory function
def create_batch_pagination_service(
    max_concurrent: int = 5, 
    delay: float = 0.5
) -> BatchPaginationService:
    """
    Create a BatchPaginationService instance.
    
    Args:
        max_concurrent: Maximum concurrent requests
        delay: Delay between requests
        
    Returns:
        BatchPaginationService instance
    """
    return BatchPaginationService(
        max_concurrent_requests=max_concurrent,
        delay_between_requests=delay
    )