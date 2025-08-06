"""Crawl service for handling web crawling operations."""

import logging
from typing import Dict, Any, Optional

from app.clients.crawl4ai_client import Crawl4aiClient
from app.models.crawl import CrawlRequest, CrawlResponse, CrawlResult
from app.utils.logging_decorators import log_operation

logger = logging.getLogger(__name__)


class CrawlService:
    """Service for crawl operations with async context manager support."""
    
    def __init__(self):
        """Initialize crawl service."""
        self.crawl4ai_client = Crawl4aiClient()
    
    async def __aenter__(self):
        """Async context manager entry."""
        logger.debug("Initializing CrawlService")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        logger.debug("Cleaning up CrawlService")
        if exc_type:
            logger.error(f"CrawlService exited with exception: {exc_type.__name__}: {exc_val}")
    
    @log_operation("crawl_url")
    async def crawl(self, request: CrawlRequest) -> CrawlResponse:
        """
        Crawl a URL using Crawl4ai.
        
        Args:
            request: Crawl request parameters
            
        Returns:
            CrawlResponse with crawl results
        """
        logger.info(f"Crawling URL: {request.url}")
        
        try:
            # Perform crawling using client
            client_result = await self.crawl4ai_client.crawl_url(
                url=str(request.url),
                include_raw_html=request.include_raw_html or False,
                word_count_threshold=request.word_count_threshold or 10,
                extraction_strategy=request.extraction_strategy or "NoExtractionStrategy",
                chunking_strategy=request.chunking_strategy or "RegexChunking",
                css_selector=request.css_selector,
                user_agent=request.user_agent,
                headers=request.headers
            )
            
            # Parse result data if successful
            crawl_result = None
            if client_result.get("success") and client_result.get("result"):
                result_data = client_result["result"]
                crawl_result = CrawlResult(
                    url=result_data["url"],
                    title=result_data.get("title"),
                    markdown=result_data.get("markdown"),
                    cleaned_html=result_data.get("cleaned_html"),
                    media=result_data.get("media"),
                    links=result_data.get("links"),
                    metadata=result_data.get("metadata", {})
                )
            
            # Create response
            response = CrawlResponse(
                success=client_result.get("success", False),
                url=request.url,
                result=crawl_result,
                error=client_result.get("error"),
                execution_time=client_result.get("execution_time", 0.0)
            )
            
            if response.success:
                logger.info(f"Successfully crawled {request.url} in {response.execution_time:.2f}s")
            else:
                logger.warning(f"Crawl failed for {request.url}: {response.error}")
            
            return response
            
        except Exception as e:
            error_msg = f"CrawlService error for {request.url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return CrawlResponse(
                success=False,
                url=request.url,
                result=None,
                error=error_msg,
                execution_time=0.0
            )