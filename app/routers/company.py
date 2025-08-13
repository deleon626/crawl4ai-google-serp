"""Company Information Extraction API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.company import (
    CompanyInformationRequest, 
    CompanyExtractionResponse,
    ExtractionMode
)
from app.services.company_service import CompanyExtractionService
from app.services.batch_company_service import BatchCompanyService, BatchRequest, BatchPriority, BatchStatus
from app.services.concurrent_extraction import ConcurrencyConfig
from app.utils.logging_decorators import log_operation
from app.utils.exceptions import (
    CompanyAnalysisError,
    create_error_response,
    generate_trace_id
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Company"])


async def get_company_service() -> CompanyExtractionService:
    """Dependency to provide CompanyExtractionService instance."""
    return CompanyExtractionService()


# Global batch service instance
_batch_service: Optional[BatchCompanyService] = None


async def get_batch_service() -> BatchCompanyService:
    """Dependency to provide BatchCompanyService instance."""
    global _batch_service
    
    if _batch_service is None:
        concurrency_config = ConcurrencyConfig(
            max_concurrent_extractions=8,
            max_concurrent_searches=12,
            max_concurrent_crawls=10,
            batch_size=20
        )
        _batch_service = BatchCompanyService(concurrency_config, max_concurrent_batches=3)
        await _batch_service.start()
    
    return _batch_service


# Batch processing request models
class BatchExtractionRequest(BaseModel):
    """Request model for batch company extraction."""
    company_names: List[str] = Field(..., min_items=1, max_items=100, description="List of company names to extract (1-100)")
    extraction_mode: ExtractionMode = Field(default=ExtractionMode.STANDARD, description="Extraction mode")
    priority: BatchPriority = Field(default=BatchPriority.NORMAL, description="Processing priority")
    country: str = Field(default="US", description="Country code for search")
    language: str = Field(default="en", description="Language code for search")
    domain_hints: Optional[Dict[str, str]] = Field(default=None, description="Optional domain hints for companies")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Max concurrent extractions")
    timeout_seconds: int = Field(default=300, ge=30, le=600, description="Timeout per company in seconds")
    include_failed_results: bool = Field(default=True, description="Include failed extractions in results")
    export_format: str = Field(default="json", regex="^(json|csv|excel)$", description="Export format")


class BatchStatusResponse(BaseModel):
    """Response model for batch status."""
    batch_id: str
    status: str
    progress: Dict[str, Any]
    processing_time: Optional[float] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    export_path: Optional[str] = None
    estimated_completion: Optional[str] = None
    last_update: Optional[str] = None


class BatchSubmissionResponse(BaseModel):
    """Response model for batch submission."""
    batch_id: str
    status: str
    message: str
    total_companies: int
    estimated_processing_time: Optional[float] = None


@router.post(
    "/extract",
    response_model=CompanyExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Company Information",
    description="Extract comprehensive company information from web sources using intelligent search and crawling",
    response_description="Company information extraction results with metadata"
)
@log_operation("company_extract")
async def extract_company_information(
    request: CompanyInformationRequest
) -> CompanyExtractionResponse:
    """
    Extract comprehensive company information from web sources.
    
    This endpoint orchestrates a multi-step process to gather company information:
    1. Discovers relevant URLs through intelligent search queries
    2. Crawls discovered pages with priority scoring
    3. Parses and aggregates information from multiple sources
    4. Returns structured company data with confidence scoring
    
    **Extraction Modes:**
    - `basic`: Essential company information only
    - `comprehensive`: Full information extraction (recommended)
    - `contact_focused`: Prioritize contact information
    - `financial_focused`: Prioritize financial and funding data
    
    **Features:**
    - Intelligent URL discovery and priority scoring
    - Multi-source information aggregation
    - Confidence scoring and data quality assessment
    - Error handling and partial result recovery
    - Rate limiting and timeout management
    
    Args:
        request: Company information extraction request with search parameters
        
    Returns:
        CompanyExtractionResponse: Structured company information with extraction metadata
        
    Raises:
        HTTPException: 
            - 422: Invalid request parameters
            - 429: Rate limit exceeded
            - 500: Internal extraction error
            - 504: Request timeout
    """
    try:
        logger.info(f"Company extraction request for '{request.company_name}' "
                   f"(mode: {request.extraction_mode}, domain: {request.domain})")
        
        # Validate extraction parameters
        _validate_extraction_request(request)
        
        # Execute extraction using service
        async with CompanyExtractionService() as service:
            result = await service.extract_company_information(request)
            
            # Log extraction results
            if result.success:
                logger.info(f"Company extraction successful for '{request.company_name}' "
                           f"(confidence: {result.company_information.confidence_score:.2f}, "
                           f"sources: {len(result.extraction_metadata.sources_found)})")
            else:
                logger.warning(f"Company extraction failed for '{request.company_name}' "
                              f"(errors: {len(result.errors)})")
            
            return result
            
    except ValueError as e:
        # Request validation errors
        logger.error(f"Validation error for company '{request.company_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "type": "validation_error",
                "company_name": request.company_name
            }
        )
    
    except CompanyAnalysisError as e:
        # Company-specific analysis errors
        logger.error(f"Company analysis error for '{request.company_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Company Analysis Error",
                "message": "Failed to analyze company information from available sources",
                "type": "analysis_error",
                "company_name": request.company_name,
                "details": str(e)
            }
        )
    
    except Exception as e:
        # Unexpected errors
        trace_id = generate_trace_id()
        logger.error(f"Unexpected error in company extraction for '{request.company_name}' "
                    f"[trace_id={trace_id}]: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred during company extraction",
                "type": "server_error",
                "company_name": request.company_name,
                "trace_id": trace_id
            }
        )


@router.post(
    "/search-and-extract",
    response_model=CompanyExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Combined Search and Extract",
    description="One-step company discovery and information extraction with enhanced search capabilities"
)
@log_operation("company_search_extract")
async def search_and_extract_company(
    company_name: str,
    domain: str = None,
    extraction_mode: ExtractionMode = ExtractionMode.COMPREHENSIVE,
    country: str = "US",
    language: str = "en",
    include_social_media: bool = True,
    include_financial_data: bool = True,
    include_contact_info: bool = True,
    max_pages_to_crawl: int = 5
) -> CompanyExtractionResponse:
    """
    Combined search and extraction endpoint for simplified company discovery.
    
    This endpoint provides a streamlined interface for company information extraction
    with common parameters exposed as query parameters for easy integration.
    
    **Quick Start Examples:**
    - Basic extraction: `POST /company/search-and-extract?company_name=OpenAI`
    - With domain: `POST /company/search-and-extract?company_name=OpenAI&domain=openai.com`
    - Contact focused: `POST /company/search-and-extract?company_name=OpenAI&extraction_mode=contact_focused`
    
    Args:
        company_name: Company name to search for (required)
        domain: Company domain if known (optional)
        extraction_mode: Level of information extraction
        country: Country code for search localization
        language: Language code for search
        include_social_media: Extract social media profiles
        include_financial_data: Extract financial information
        include_contact_info: Extract contact details
        max_pages_to_crawl: Maximum pages to crawl
        
    Returns:
        CompanyExtractionResponse: Company information extraction results
    """
    # Build request from parameters
    request = CompanyInformationRequest(
        company_name=company_name,
        domain=domain,
        extraction_mode=extraction_mode,
        country=country,
        language=language,
        include_social_media=include_social_media,
        include_financial_data=include_financial_data,
        include_contact_info=include_contact_info,
        max_pages_to_crawl=max_pages_to_crawl
    )
    
    # Delegate to main extraction endpoint
    return await extract_company_information(request)


@router.get(
    "/extraction-scopes",
    status_code=status.HTTP_200_OK,
    summary="Available Extraction Scopes",
    description="Get available extraction modes and their capabilities"
)
async def get_extraction_scopes() -> Dict[str, Any]:
    """
    Get available extraction scopes and their capabilities.
    
    Returns information about different extraction modes, their features,
    and recommended use cases to help clients choose the appropriate scope.
    
    Returns:
        Dict containing extraction modes, features, and recommendations
    """
    return {
        "extraction_modes": {
            "basic": {
                "description": "Essential company information only",
                "features": [
                    "Company name and domain",
                    "Basic business description",
                    "Industry and sector classification",
                    "Headquarters location"
                ],
                "estimated_time": "15-30 seconds",
                "recommended_for": "Quick company validation and basic profiling",
                "typical_pages_crawled": "2-3"
            },
            "comprehensive": {
                "description": "Full information extraction with all available data",
                "features": [
                    "Complete basic information",
                    "Contact details (email, phone, address)",
                    "Social media profiles",
                    "Financial information (funding, valuation)",
                    "Key personnel (optional)",
                    "Multiple office locations"
                ],
                "estimated_time": "45-90 seconds",
                "recommended_for": "Complete company analysis and due diligence",
                "typical_pages_crawled": "5-8"
            },
            "contact_focused": {
                "description": "Prioritize contact information extraction",
                "features": [
                    "Primary and alternative email addresses",
                    "Phone and fax numbers",
                    "Physical addresses",
                    "Contact forms and support channels",
                    "Basic company information"
                ],
                "estimated_time": "20-40 seconds",
                "recommended_for": "Lead generation and outreach preparation",
                "typical_pages_crawled": "3-5"
            },
            "financial_focused": {
                "description": "Prioritize financial and funding information",
                "features": [
                    "Funding rounds and total raised",
                    "Investor information",
                    "Company valuation",
                    "Revenue estimates",
                    "Stock information (if public)",
                    "Financial news and updates"
                ],
                "estimated_time": "30-60 seconds",
                "recommended_for": "Investment research and financial analysis",
                "typical_pages_crawled": "4-6"
            }
        },
        "additional_options": {
            "include_subsidiaries": "Extract information about subsidiary companies",
            "include_social_media": "Extract social media profiles and follower counts",
            "include_key_personnel": "Extract leadership and key employee information",
            "custom_timeout": "Configure crawl timeout (5-120 seconds per page)",
            "max_pages_control": "Control crawling depth (1-20 pages)"
        },
        "quality_indicators": {
            "confidence_score": "Overall confidence in extracted data (0.0-1.0)",
            "data_quality_score": "Assessment of data accuracy and completeness",
            "completeness_score": "Percentage of requested information fields found",
            "sources_found": "Number of web sources used for information aggregation"
        },
        "rate_limits": {
            "requests_per_minute": 10,
            "concurrent_extractions": 3,
            "daily_limit": 1000
        }
    }


# Batch Processing Endpoints

@router.post(
    "/batch/submit",
    response_model=BatchSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Batch Company Extraction",
    description="Submit a batch of companies for parallel extraction processing with intelligent scheduling"
)
@log_operation("batch_company_submit")
async def submit_batch_extraction(
    request: BatchExtractionRequest,
    batch_service: BatchCompanyService = Depends(get_batch_service)
) -> BatchSubmissionResponse:
    """
    Submit batch company extraction request for asynchronous processing.
    
    This endpoint allows you to submit multiple companies for extraction in a single request,
    with intelligent scheduling, priority management, and progress tracking.
    
    **Features:**
    - Process 1-100 companies in parallel
    - Priority-based scheduling (low, normal, high, urgent)
    - Export results in multiple formats (JSON, CSV, Excel)
    - Real-time progress tracking
    - Automatic caching and optimization
    
    **Example Request:**
    ```json
    {
        "company_names": ["OpenAI", "Microsoft", "Google"],
        "extraction_mode": "comprehensive",
        "priority": "high",
        "export_format": "json"
    }
    ```
    
    Args:
        request: Batch extraction request parameters
        
    Returns:
        BatchSubmissionResponse: Batch submission confirmation with batch ID for tracking
    """
    try:
        logger.info(f"Submitting batch extraction for {len(request.company_names)} companies")
        
        # Estimate processing time (rough calculation)
        estimated_time = len(request.company_names) * 15.0  # ~15 seconds per company average
        
        # Submit batch for processing
        batch_id = await batch_service.submit_batch(
            company_names=request.company_names,
            extraction_mode=request.extraction_mode,
            priority=request.priority,
            country=request.country,
            language=request.language,
            domain_hints=request.domain_hints,
            max_concurrent=request.max_concurrent,
            timeout_seconds=request.timeout_seconds,
            include_failed_results=request.include_failed_results,
            export_format=request.export_format
        )
        
        logger.info(f"Batch submitted successfully: {batch_id}")
        
        return BatchSubmissionResponse(
            batch_id=batch_id,
            status="queued",
            message=f"Batch extraction submitted for {len(request.company_names)} companies",
            total_companies=len(request.company_names),
            estimated_processing_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Batch submission failed: {str(e)}")
        trace_id = generate_trace_id()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                error_type="BatchSubmissionError",
                message=f"Failed to submit batch extraction: {str(e)}",
                details={"trace_id": trace_id}
            )
        )


@router.get(
    "/batch/{batch_id}/status",
    response_model=BatchStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Batch Processing Status",
    description="Get real-time status and progress information for a batch processing job"
)
@log_operation("batch_company_status")
async def get_batch_status(
    batch_id: str,
    batch_service: BatchCompanyService = Depends(get_batch_service)
) -> BatchStatusResponse:
    """
    Get batch processing status and progress information.
    
    This endpoint provides real-time status updates for batch processing jobs,
    including progress metrics, estimated completion time, and processing statistics.
    
    **Status Values:**
    - `queued`: Batch is waiting to be processed
    - `processing`: Batch is currently being processed
    - `completed`: Batch processing completed successfully
    - `partially_completed`: Some companies succeeded, others failed
    - `failed`: Batch processing failed
    
    Args:
        batch_id: Unique batch identifier from submission response
        
    Returns:
        BatchStatusResponse: Current batch status and progress information
    """
    try:
        logger.debug(f"Getting status for batch: {batch_id}")
        
        batch_status = await batch_service.get_batch_status(batch_id)
        
        return BatchStatusResponse(
            batch_id=batch_id,
            status=batch_status["status"],
            progress=batch_status["progress"],
            processing_time=batch_status.get("processing_time"),
            created_at=batch_status.get("created_at"),
            completed_at=batch_status.get("completed_at"),
            export_path=batch_status.get("export_path"),
            estimated_completion=batch_status.get("estimated_completion"),
            last_update=batch_status.get("last_update")
        )
        
    except Exception as e:
        logger.error(f"Failed to get batch status for {batch_id}: {str(e)}")
        trace_id = generate_trace_id()
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=create_error_response(
                error_type="BatchNotFound",
                message=f"Batch {batch_id} not found or status unavailable: {str(e)}",
                details={"batch_id": batch_id, "trace_id": trace_id}
            )
        )


@router.get(
    "/batch/{batch_id}/results",
    status_code=status.HTTP_200_OK,
    summary="Get Batch Processing Results",
    description="Retrieve complete results from a finished batch processing job"
)
@log_operation("batch_company_results")
async def get_batch_results(
    batch_id: str,
    batch_service: BatchCompanyService = Depends(get_batch_service)
) -> Dict[str, Any]:
    """
    Get complete batch processing results.
    
    This endpoint returns the complete results from a finished batch processing job,
    including all successful and failed company extractions, summary statistics,
    and export file information.
    
    **Note:** Results are only available for completed batches. Use the status endpoint
    to check if a batch is finished before requesting results.
    
    Args:
        batch_id: Unique batch identifier from submission response
        
    Returns:
        Dict containing complete batch results, summary statistics, and export information
    """
    try:
        logger.debug(f"Getting results for batch: {batch_id}")
        
        batch_result = await batch_service.get_batch_result(batch_id)
        
        if batch_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    error_type="BatchNotFound",
                    message=f"Batch {batch_id} not found or results not available",
                    details={"batch_id": batch_id}
                )
            )
        
        # Convert results to response format
        results_data = {
            "batch_id": batch_result.batch_id,
            "status": batch_result.status.value,
            "summary": {
                "total_companies": batch_result.total_companies,
                "successful_extractions": batch_result.successful_extractions,
                "failed_extractions": batch_result.failed_extractions,
                "success_rate": (batch_result.successful_extractions / batch_result.total_companies * 100) if batch_result.total_companies > 0 else 0,
                "processing_time": batch_result.processing_time,
                "created_at": batch_result.created_at.isoformat(),
                "completed_at": batch_result.completed_at.isoformat() if batch_result.completed_at else None
            },
            "export_info": {
                "export_path": batch_result.export_path,
                "format": "json"  # TODO: Get from batch request
            },
            "summary_stats": batch_result.summary_stats or {},
            "results": {}
        }
        
        # Add individual company results
        for company_name, response in batch_result.results.items():
            results_data["results"][company_name] = {
                "success": response.success,
                "processing_time": response.processing_time,
                "company_information": response.company_information.dict() if response.company_information else None,
                "errors": [error.dict() for error in response.errors],
                "warnings": response.warnings
            }
        
        return results_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch results for {batch_id}: {str(e)}")
        trace_id = generate_trace_id()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                error_type="BatchResultsError",
                message=f"Failed to retrieve batch results: {str(e)}",
                details={"batch_id": batch_id, "trace_id": trace_id}
            )
        )


@router.get(
    "/batch/stats",
    status_code=status.HTTP_200_OK,
    summary="Get Batch Processing Statistics",
    description="Get comprehensive statistics about batch processing performance and queue status"
)
@log_operation("batch_company_stats")
async def get_batch_statistics(
    batch_service: BatchCompanyService = Depends(get_batch_service)
) -> Dict[str, Any]:
    """
    Get batch processing service statistics.
    
    This endpoint provides comprehensive statistics about the batch processing service,
    including queue status, performance metrics, and resource utilization.
    
    Returns:
        Dict containing batch service statistics and performance metrics
    """
    try:
        logger.debug("Getting batch processing statistics")
        
        stats = await batch_service.get_service_stats()
        
        return {
            "service": "batch_company_extraction",
            "status": "operational",
            "statistics": stats,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Add actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to get batch statistics: {str(e)}")
        trace_id = generate_trace_id()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                error_type="BatchStatsError",
                message=f"Failed to retrieve batch statistics: {str(e)}",
                details={"trace_id": trace_id}
            )
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Company Service Health Check",
    description="Check the health and availability of the company extraction service and its dependencies"
)
async def company_service_health() -> Dict[str, Any]:
    """
    Check company extraction service health and dependencies.
    
    This endpoint provides health information for the company extraction service
    and its dependencies including SERP search, web crawling, and parsing capabilities.
    
    Returns:
        Dict containing service health status and dependency information
    """
    try:
        # Test service initialization
        async with CompanyExtractionService() as service:
            status_info = await service.get_service_status()
            
            return {
                "service": "company_extraction",
                "status": "healthy",
                "version": "1.0.0",
                "capabilities": {
                    "extraction_modes": 4,
                    "supported_languages": ["en", "es", "fr", "de", "ja", "zh", "pt", "it", "ru", "ko"],
                    "supported_countries": "All ISO 3166-1 alpha-2 codes",
                    "max_concurrent_extractions": 3,
                    "max_pages_per_extraction": 20
                },
                "dependencies": {
                    "serp_service": status_info.get("serp_service_status", "unknown"),
                    "crawl_service": "available" if status_info.get("crawl_service_initialized") else "unavailable",
                    "parser_service": "available" if status_info.get("parser_initialized") else "unavailable",
                    "external_apis": {
                        "bright_data": status_info.get("serp_service_status", "unknown"),
                        "crawl4ai": "available" if status_info.get("crawl_service_initialized") else "unavailable"
                    }
                },
                "performance": {
                    "average_extraction_time": "45-90 seconds",
                    "success_rate": ">90%",
                    "data_quality_score": ">0.8"
                }
            }
            
    except Exception as e:
        logger.error(f"Company service health check failed: {str(e)}")
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "service": "company_extraction",
                "status": "degraded",
                "version": "1.0.0",
                "error": str(e),
                "dependencies": {
                    "serp_service": "unknown",
                    "crawl_service": "unknown",
                    "parser_service": "unknown",
                    "external_apis": {
                        "bright_data": "unknown",
                        "crawl4ai": "unknown"
                    }
                }
            }
        )


def _validate_extraction_request(request: CompanyInformationRequest) -> None:
    """
    Validate company extraction request parameters.
    
    Args:
        request: Company extraction request to validate
        
    Raises:
        ValueError: If request parameters are invalid
    """
    # Company name validation
    if not request.company_name or len(request.company_name.strip()) < 2:
        raise ValueError("Company name must be at least 2 characters long")
    
    if len(request.company_name) > 100:
        raise ValueError("Company name must be less than 100 characters")
    
    # Domain validation (if provided)
    if request.domain:
        if len(request.domain) > 100:
            raise ValueError("Domain must be less than 100 characters")
    
    # Crawl limits validation
    if request.max_pages_to_crawl > 20:
        raise ValueError("Maximum pages to crawl cannot exceed 20")
    
    if request.timeout_seconds > 120:
        raise ValueError("Timeout cannot exceed 120 seconds per page")
    
    # Ensure reasonable extraction scope
    if (not request.include_contact_info and 
        not request.include_social_media and 
        not request.include_financial_data and
        request.extraction_mode == ExtractionMode.BASIC):
        raise ValueError("At least one information type must be included for extraction")