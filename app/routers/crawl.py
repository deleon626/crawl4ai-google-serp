"""Crawl API endpoints."""

import logging
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import HttpUrl

from app.models.crawl import CrawlRequest, CrawlResponse
from app.models.instagram import (
    InstagramAnalysisRequest, InstagramAnalysisResponse, InstagramAnalysisResult,
    InstagramSearchRequest, InstagramSearchResponse,
    BusinessAnalysis, BusinessIndicators, ExtractedData,
    LinkAnalysis, LinkInfo, KeywordAnalysis, KeywordInfo
)
from app.services.crawl_service import CrawlService
from app.services.instagram_service import InstagramSearchService
from app.services.link_validation_service import LinkValidationService
from app.services.keyword_extraction_service import KeywordExtractionService
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


@router.post("/analyze/instagram", response_model=InstagramAnalysisResponse, summary="Analyze Instagram profile")
@log_operation("instagram_analysis_endpoint")
async def analyze_instagram_profile(
    request: InstagramAnalysisRequest
) -> InstagramAnalysisResponse:
    """
    Analyze an Instagram profile for business indicators and extract content.
    
    This endpoint crawls an Instagram profile URL and analyzes the content
    for business indicators, contact information, links, and keywords.
    
    Args:
        request: Instagram analysis request with URL and analysis options
        
    Returns:
        InstagramAnalysisResponse with comprehensive business analysis
    """
    start_time = time.time()
    
    try:
        instagram_service = InstagramSearchService()
        
        # Step 1: Crawl the profile if requested
        crawl_result = None
        if request.crawl_content:
            crawl_request = CrawlRequest(
                url=request.url,
                include_raw_html=False,
                word_count_threshold=5,
                extraction_strategy="NoExtractionStrategy",
                chunking_strategy="RegexChunking"
            )
            
            async with CrawlService() as crawl_service:
                crawl_response = await crawl_service.crawl(crawl_request)
                if crawl_response.success:
                    crawl_result = crawl_response.result
        
        if not crawl_result:
            return InstagramAnalysisResponse(
                success=False,
                result=None,
                error="Failed to crawl Instagram profile content",
                execution_time=time.time() - start_time
            )
        
        # Prepare profile data for analysis
        profile_data = {
            "url": str(request.url),
            "title": crawl_result.title or "",
            "description": crawl_result.markdown or "",
            "timestamp": crawl_result.metadata.get("timestamp") if crawl_result.metadata else None
        }
        
        # Step 2: Analyze for business indicators
        analysis_result = await instagram_service.analyze_instagram_profile(profile_data)
        
        # Step 3: Extract and validate links if requested
        link_analysis = None
        if request.extract_links and crawl_result.markdown:
            link_service = LinkValidationService()
            link_result = await link_service.extract_and_validate_links(
                text=crawl_result.markdown,
                validate_links=request.validate_links
            )
            
            # Convert to response models
            link_info_list = []
            for link in link_result["all_links"]:
                link_info_list.append(LinkInfo(
                    url=link.url,
                    original_text=link.original_text,
                    link_type=link.link_type,
                    domain=link.domain,
                    is_business_link=link.is_business_link,
                    confidence=link.confidence,
                    validation_status=link.validation_status,
                    response_time=link.response_time,
                    status_code=link.status_code
                ))
            
            link_analysis = LinkAnalysis(
                total_links=link_result["total_links"],
                business_links=[info for info in link_info_list if info.is_business_link],
                social_links=[info for info in link_info_list if info.link_type == "social"],
                contact_links=[info for info in link_info_list if info.link_type in ["email", "phone"]],
                website_links=[info for info in link_info_list if info.link_type == "website"],
                summary=link_result["summary"]
            )
        
        # Step 4: Extract keywords if requested
        keyword_analysis = None
        if request.extract_keywords and crawl_result.markdown:
            keyword_service = KeywordExtractionService()
            keyword_result = await keyword_service.extract_and_group_keywords(
                text=crawl_result.markdown,
                max_keywords=20,
                include_phrases=True,
                group_keywords=True
            )
            
            # Convert to response models
            keyword_info_list = []
            for keyword in keyword_result["keywords"]:
                keyword_info_list.append(KeywordInfo(
                    keyword=keyword.keyword,
                    frequency=keyword.frequency,
                    relevance_score=keyword.relevance_score,
                    category=keyword.category,
                    variations=keyword.variations,
                    context_examples=keyword.context_examples
                ))
            
            # Convert groups
            groups_dict = {}
            for group_name, group_keywords in keyword_result["groups"].items():
                groups_dict[group_name] = [
                    KeywordInfo(
                        keyword=kw.keyword,
                        frequency=kw.frequency,
                        relevance_score=kw.relevance_score,
                        category=kw.category,
                        variations=kw.variations,
                        context_examples=kw.context_examples
                    ) for kw in group_keywords
                ]
            
            top_business_keywords = []
            for kw in keyword_result["top_business_keywords"]:
                top_business_keywords.append(KeywordInfo(
                    keyword=kw.keyword,
                    frequency=kw.frequency,
                    relevance_score=kw.relevance_score,
                    category=kw.category,
                    variations=kw.variations,
                    context_examples=kw.context_examples
                ))
            
            keyword_analysis = KeywordAnalysis(
                keywords=keyword_info_list,
                groups=groups_dict,
                summary=keyword_result["summary"],
                top_business_keywords=top_business_keywords
            )
        
        # Create comprehensive result
        business_indicators = BusinessIndicators(
            contact_info=analysis_result["business_analysis"]["indicators"]["contact_info"],
            business_signals=analysis_result["business_analysis"]["indicators"]["business_signals"],
            professional_markers=analysis_result["business_analysis"]["indicators"]["professional_markers"],
            location_info=analysis_result["business_analysis"]["indicators"]["location_info"]
        )
        
        extracted_data = ExtractedData(
            emails=analysis_result["business_analysis"]["extracted_data"]["emails"],
            phones=analysis_result["business_analysis"]["extracted_data"]["phones"],
            websites=analysis_result["business_analysis"]["extracted_data"]["websites"],
            social_handles=analysis_result["business_analysis"]["extracted_data"]["social_handles"]
        )
        
        business_analysis = BusinessAnalysis(
            is_business=analysis_result["business_analysis"]["is_business"],
            confidence=analysis_result["business_analysis"]["confidence"],
            indicators=business_indicators,
            extracted_data=extracted_data
        )
        
        instagram_result = InstagramAnalysisResult(
            profile_url=request.url,
            profile_title=analysis_result["profile_title"],
            business_analysis=business_analysis,
            business_category=analysis_result["business_category"],
            link_analysis=link_analysis,
            keyword_analysis=keyword_analysis,
            crawl_success=True,
            analysis_timestamp=analysis_result["analysis_timestamp"],
            metadata=analysis_result["metadata"]
        )
        
        execution_time = time.time() - start_time
        
        return InstagramAnalysisResponse(
            success=True,
            result=instagram_result,
            error=None,
            execution_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Instagram analysis error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return InstagramAnalysisResponse(
            success=False,
            result=None,
            error=error_msg,
            execution_time=execution_time
        )


@router.post("/search/instagram", response_model=InstagramSearchResponse, summary="Search for Instagram business profiles")
@log_operation("instagram_search_endpoint")
async def search_instagram_businesses(
    request: InstagramSearchRequest
) -> InstagramSearchResponse:
    """
    Generate optimized search queries for finding Instagram business profiles.
    
    This endpoint creates specialized Google search queries designed to find
    Instagram business profiles based on business type, location, and keywords.
    
    Args:
        request: Instagram search request with business criteria
        
    Returns:
        InstagramSearchResponse with generated queries and optional results
    """
    start_time = time.time()
    
    try:
        instagram_service = InstagramSearchService()
        
        # Generate search queries
        queries = await instagram_service.build_business_search_queries(
            business_type=request.business_type,
            location=request.location,
            keywords=request.keywords
        )
        
        execution_time = time.time() - start_time
        
        return InstagramSearchResponse(
            success=True,
            queries=queries,
            search_results=None,  # TODO: Integrate with SERP service for actual search
            analyzed_profiles=None,  # TODO: Integrate profile analysis
            total_results=len(queries),
            execution_time=execution_time,
            error=None
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Instagram search error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return InstagramSearchResponse(
            success=False,
            queries=[],
            search_results=None,
            analyzed_profiles=None,
            total_results=0,
            execution_time=execution_time,
            error=error_msg
        )