"""
Company analysis API endpoints.
Handles company website discovery, content analysis, and employee extraction.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.company import (
    CompanyAnalysisRequest, CompanyAnalysisResponse,
    CompanySearchRequest, CompanySearchResponse
)
from app.services.company_analysis_service import CompanyAnalysisService
from app.utils.logging_decorators import log_operation

router = APIRouter(
    prefix="/api/v1/company",
    tags=["Company Analysis"]
)


@router.post("/analyze", response_model=CompanyAnalysisResponse)
@log_operation("company_analysis_endpoint")
async def analyze_company(request: CompanyAnalysisRequest) -> CompanyAnalysisResponse:
    """
    Analyze company information including website discovery and employee extraction.
    
    **Features:**
    - Company website discovery via SERP search
    - Website content analysis and extraction
    - Employee identification from website content  
    - Contact information extraction
    - Business intelligence gathering
    
    **Input Requirements:**
    - At least one of: company_name, company_url, or linkedin_url must be provided
    
    **Response Includes:**
    - Company information and metadata
    - Website analysis results
    - Employee profiles with confidence scores
    - Discovery statistics and metrics
    """
    async with CompanyAnalysisService() as service:
        return await service.analyze_company(request)


@router.post("/search-queries", response_model=CompanySearchResponse)  
@log_operation("company_search_queries_endpoint")
async def generate_company_search_queries(request: CompanySearchRequest) -> CompanySearchResponse:
    """
    Generate optimized search queries for company discovery.
    
    **Features:**
    - Website discovery queries
    - Employee search queries  
    - Contact information queries
    - Social profile discovery queries
    
    **Use Cases:**
    - Manual company research
    - Batch company analysis preparation
    - Search strategy optimization
    """
    from app.services.company_analysis_service import CompanyWebsiteDiscovery
    
    discovery = CompanyWebsiteDiscovery()
    search_queries = discovery.generate_search_queries(
        request.company_name,
        request.additional_keywords and ' '.join(request.additional_keywords)
    )
    
    # Add specialized queries based on search type
    specialized_queries = []
    
    if request.search_type == "employees":
        specialized_queries.extend([
            f'"{request.company_name}" team members site:linkedin.com',
            f'"{request.company_name}" employees directory',
            f'"{request.company_name}" staff "meet the team"'
        ])
    elif request.search_type == "contact":
        specialized_queries.extend([
            f'"{request.company_name}" contact information',
            f'"{request.company_name}" phone email address',
            f'"{request.company_name}" headquarters location'
        ])
    elif request.search_type == "comprehensive":
        specialized_queries.extend([
            f'"{request.company_name}" company profile',
            f'"{request.company_name}" about company information',
            f'"{request.company_name}" business overview'
        ])
    
    all_queries = search_queries + specialized_queries
    
    # Create explanations
    explanations = {}
    for i, query in enumerate(all_queries):
        if "official website" in query:
            explanations[query] = "Finds the company's primary website"
        elif "company website" in query:
            explanations[query] = "Alternative website discovery approach"
        elif "linkedin.com/company" in query:
            explanations[query] = "Locates company LinkedIn profile"
        elif "team members" in query or "employees" in query:
            explanations[query] = "Discovers employee information"
        elif "contact" in query:
            explanations[query] = "Finds contact information and location"
        else:
            explanations[query] = "General company information discovery"
    
    return CompanySearchResponse(
        search_queries=all_queries,
        query_explanations=explanations,
        estimated_results=len(all_queries) * 10,  # Rough estimate
        search_strategy=request.search_type
    )


@router.get("/test", response_model=dict)
@log_operation("company_test_endpoint")
async def test_company_analysis():
    """
    Test endpoint to verify company analysis functionality.
    
    **Returns:**
    - Service status
    - Available features
    - Configuration information
    """
    try:
        async with CompanyAnalysisService() as service:
            return {
                "status": "healthy",
                "service": "Company Analysis Service",
                "version": "1.0.0",
                "features": [
                    "Company website discovery",
                    "Website content analysis", 
                    "Employee extraction",
                    "Contact information gathering",
                    "Business intelligence analysis"
                ],
                "supported_inputs": [
                    "Company name",
                    "Company website URL", 
                    "LinkedIn company URL"
                ],
                "max_employees_per_analysis": 200,
                "supported_analysis_types": [
                    "Basic company info",
                    "Deep website analysis",
                    "Employee discovery",
                    "Contact extraction"
                ]
            }
    except Exception as e:
        return {
            "status": "error", 
            "service": "Company Analysis Service",
            "error": str(e)
        }