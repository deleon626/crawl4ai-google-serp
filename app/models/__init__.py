"""Models package."""

# SERP models
from .serp import (
    SearchRequest,
    SearchResult,
    SearchResponse,
    PaginationMetadata,
    BatchPaginationRequest,
    BatchPaginationResponse,
    PageResult,
    BatchPaginationSummary,
    MergedResultsMetadata,
    SocialPlatform,
    InstagramContentType,
    LinkedInContentType,
)

# Crawl models
from .crawl import (
    CrawlRequest,
    CrawlResponse,
)

# Company models
from .company import (
    CompanyInformationRequest,
    CompanyContact,
    CompanySocial,
    CompanyBasicInfo,
    CompanyFinancials,
    CompanyKeyPersonnel,
    CompanyInformation,
    CompanyExtractionResponse,
    ExtractionError,
    ExtractionMetadata,
    ExtractionMode,
    CompanySize,
    CompanySector,
    SocialPlatformType,
)

__all__ = [
    # SERP models
    "SearchRequest",
    "SearchResult", 
    "SearchResponse",
    "PaginationMetadata",
    "BatchPaginationRequest",
    "BatchPaginationResponse",
    "PageResult",
    "BatchPaginationSummary",
    "MergedResultsMetadata",
    "SocialPlatform",
    "InstagramContentType",
    "LinkedInContentType",
    # Crawl models
    "CrawlRequest",
    "CrawlResponse",
    # Company models
    "CompanyInformationRequest",
    "CompanyContact",
    "CompanySocial", 
    "CompanyBasicInfo",
    "CompanyFinancials",
    "CompanyKeyPersonnel",
    "CompanyInformation",
    "CompanyExtractionResponse",
    "ExtractionError",
    "ExtractionMetadata",
    "ExtractionMode",
    "CompanySize",
    "CompanySector",
    "SocialPlatformType",
]