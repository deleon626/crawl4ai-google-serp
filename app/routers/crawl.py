"""Crawl API endpoints."""

import logging
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import HttpUrl

from app.models.crawl import CrawlRequest, CrawlResponse
from app.services.crawl_service import CrawlService
from app.utils.logging_decorators import log_operation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/crawl", response_model=CrawlResponse, summary="Crawl a URL")
@log_operation("crawl_endpoint")
async def crawl_url(
    request: CrawlRequest
) -> CrawlResponse:
    """
    Crawl a single URL using Crawl4ai and return structured content.
    
    This endpoint uses Crawl4ai to extract content from web pages,
    returning structured data including text, links, images, and metadata.
    
    Args:
        request: Crawl request with URL and configuration options
        
    Returns:
        CrawlResponse with extracted content and metadata
        
    Raises:
        HTTPException: If crawling fails or URL is invalid
    """
    try:
        async with CrawlService() as crawl_service:
            result = await crawl_service.crawl(request)
            
            if not result.success and result.error:
                # Return the error response rather than raising exception
                # to provide detailed error information to the client
                logger.warning(f"Crawl request failed: {result.error}")
            
            return result
            
    except Exception as e:
        error_msg = f"Crawl endpoint error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": error_msg,
                "type": "crawl_error"
            }
        )


@router.get("/crawl/test", summary="Test crawl endpoint with sample URL")
@log_operation("crawl_test_endpoint")
async def test_crawl(
    url: str = "https://httpbin.org/html"
) -> CrawlResponse:
    """
    Test the crawl functionality with a sample URL.
    
    This endpoint provides a simple way to test the crawling functionality
    using httpbin.org/html as a default test URL.
    
    Args:
        url: URL to crawl (defaults to httpbin.org/html)
        
    Returns:
        CrawlResponse with extracted content
    """
    try:
        request = CrawlRequest(
            url=HttpUrl(url),
            include_raw_html=False,
            word_count_threshold=5,
            extraction_strategy="NoExtractionStrategy",
            chunking_strategy="RegexChunking"
        )
        
        async with CrawlService() as crawl_service:
            return await crawl_service.crawl(request)
            
    except Exception as e:
        error_msg = f"Test crawl error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Test crawl failed",
                "message": error_msg,
                "type": "test_crawl_error"
            }
        )


