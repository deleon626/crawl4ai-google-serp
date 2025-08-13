"""Company extraction service for orchestrating company information discovery and extraction."""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

from app.services.serp_service import SERPService
from app.services.crawl_service import CrawlService
from app.models.serp import SearchRequest, SocialPlatform, InstagramContentType, LinkedInContentType
from app.models.crawl import CrawlRequest
from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, CompanyInformation,
    ExtractionMetadata, ExtractionError, ExtractionMode
)
from app.parsers.company_parser import CompanyInformationParser
from app.utils.exceptions import BrightDataError
from app.utils.resilience import resilient_operation, serp_circuit_breaker, crawl_circuit_breaker, RetryConfig
from app.utils.caching import get_cache_service
from app.utils.performance import get_performance_monitor

# Set up logging
logger = logging.getLogger(__name__)


class CompanyExtractionService:
    """
    Service for extracting comprehensive company information.
    
    Orchestrates SERP search, web crawling, and parsing to extract structured
    company data from multiple sources with priority scoring and error handling.
    """
    
    def __init__(self):
        """Initialize company extraction service."""
        self.serp_service = None
        self.crawl_service = None
        self.company_parser = CompanyInformationParser()
        self.cache_service = None
        self.performance_monitor = None
        logger.info("CompanyExtractionService initialized")
    
    async def __aenter__(self):
        """Async context manager entry - initialize services."""
        logger.debug("Initializing CompanyExtractionService resources")
        self.serp_service = SERPService()
        self.crawl_service = CrawlService()
        
        # Initialize services with their context managers
        await self.serp_service.__aenter__()
        await self.crawl_service.__aenter__()
        
        # Initialize caching and performance monitoring
        try:
            self.cache_service = await get_cache_service()
            self.performance_monitor = await get_performance_monitor()
            logger.debug("Caching and performance monitoring initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize caching/performance monitoring: {e}")
            # Continue without caching/monitoring
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        logger.debug("Cleaning up CompanyExtractionService resources")
        
        # Close services
        if self.serp_service:
            await self.serp_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.crawl_service:
            await self.crawl_service.__aexit__(exc_type, exc_val, exc_tb)
        
        if exc_type:
            logger.error(f"CompanyExtractionService exited with exception: {exc_type.__name__}: {exc_val}")
    
    async def extract_company_information(
        self, 
        request: CompanyInformationRequest
    ) -> CompanyExtractionResponse:
        """
        Main orchestration method for company information extraction.
        
        Args:
            request: Company information extraction request
            
        Returns:
            CompanyExtractionResponse with extracted company data and metadata
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Starting company extraction for '{request.company_name}' "
                   f"(request_id: {request_id}, mode: {request.extraction_mode})")
        
        # Initialize response components
        errors = []
        warnings = []
        sources_found = []
        search_queries_used = []
        pages_crawled = 0
        pages_attempted = 0
        company_information = None
        
        try:
            # Check cache first if available
            cache_key = None
            if self.cache_service:
                cached_result = await self.cache_service.get_company_info(
                    request.company_name, 
                    request.domain,
                    request.extraction_mode.value
                )
                
                if cached_result:
                    logger.info(f"Cache hit for company: {request.company_name}")
                    
                    # Record cache hit metric
                    if self.performance_monitor:
                        await self.performance_monitor.record_metric(
                            "cache_hits", 1.0, "count", 
                            {"company": request.company_name, "type": "company_info"}
                        )
                    
                    # Convert cached data to CompanyInformation
                    try:
                        company_information = CompanyInformation(**cached_result)
                        
                        extraction_metadata = ExtractionMetadata(
                            pages_crawled=0,
                            pages_attempted=0,
                            extraction_time=0.001,  # Minimal time for cache hit
                            sources_found=["cache"],
                            search_queries_used=[],
                            extraction_mode_used=request.extraction_mode
                        )
                        
                        return CompanyExtractionResponse(
                            request_id=request_id,
                            company_name=request.company_name,
                            success=True,
                            company_information=company_information,
                            extraction_metadata=extraction_metadata,
                            errors=[],
                            warnings=["Result served from cache"],
                            processing_time=time.time() - start_time
                        )
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse cached data for {request.company_name}: {e}")
                        # Continue with normal extraction
                        
            # Record cache miss metric
            if self.performance_monitor:
                await self.performance_monitor.record_metric(
                    "cache_misses", 1.0, "count", 
                    {"company": request.company_name, "type": "company_info"}
                )
            
            # Step 1: Discover company URLs through SERP search (with resilience)
            logger.debug("Step 1: URL discovery via SERP search")
            try:
                url_candidates = await self._discover_company_urls_resilient(
                    request, search_queries_used, errors
                )
            except Exception as e:
                logger.error(f"Resilient URL discovery failed: {e}")
                url_candidates = []  # Fallback to empty list
            
            if not url_candidates:
                logger.warning(f"No URLs discovered for {request.company_name}")
                warnings.append("No relevant URLs found through search")
            
            # Step 2: Crawl discovered URLs with priority scoring (with resilience)
            logger.debug("Step 2: Crawling priority URLs")
            try:
                crawl_results, pages_crawled, pages_attempted = await self._crawl_company_pages_resilient(
                    url_candidates, request, errors
                )
            except Exception as e:
                logger.error(f"Resilient crawling failed: {e}")
                crawl_results = []
                pages_crawled = 0
                pages_attempted = len(url_candidates)
            
            if not crawl_results:
                logger.warning(f"No content successfully crawled for {request.company_name}")
                warnings.append("No web content successfully crawled")
            
            # Step 3: Parse and aggregate company information
            logger.debug("Step 3: Parsing company information")
            if crawl_results:
                company_information = await self._parse_company_information(
                    crawl_results, request.company_name, sources_found, errors
                )
                
                # Cache successful extraction if caching available
                if company_information and self.cache_service:
                    try:
                        await self.cache_service.set_company_info(
                            request.company_name,
                            company_information,
                            request.domain,
                            request.extraction_mode.value
                        )
                        logger.debug(f"Cached company information for: {request.company_name}")
                    except Exception as e:
                        logger.warning(f"Failed to cache company information: {e}")
            
            # Determine success status and final validation
            success = company_information is not None
            
            # If no company information found, raise specific error
            if not success:
                raise CompanyNotFoundError(
                    request.company_name,
                    f"No company information could be extracted from {pages_attempted} pages",
                    {
                        "request_id": request_id,
                        "pages_attempted": pages_attempted,
                        "sources_searched": len(search_queries_used),
                        "extraction_mode": request.extraction_mode
                    }
                )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create extraction metadata
            extraction_metadata = ExtractionMetadata(
                pages_crawled=pages_crawled,
                pages_attempted=pages_attempted,
                extraction_time=processing_time,
                sources_found=sources_found,
                search_queries_used=search_queries_used,
                extraction_mode_used=request.extraction_mode
            )
            
            logger.info(f"Company extraction completed for '{request.company_name}' "
                       f"(success: {success}, time: {processing_time:.2f}s, "
                       f"pages: {pages_crawled}/{pages_attempted})")
            
            # Record performance metrics
            if self.performance_monitor:
                await self.performance_monitor.record_metric(
                    "extraction_time", processing_time, "seconds",
                    {"company": request.company_name, "success": str(success)}
                )
                await self.performance_monitor.record_metric(
                    "pages_crawled", float(pages_crawled), "count",
                    {"company": request.company_name}
                )
            
            return CompanyExtractionResponse(
                request_id=request_id,
                company_name=request.company_name,
                success=success,
                company_information=company_information,
                extraction_metadata=extraction_metadata,
                errors=errors,
                warnings=warnings,
                processing_time=processing_time
            )
            
        except Exception as e:
            error_msg = f"Company extraction service error for {request.company_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Add to errors list
            errors.append(ExtractionError(
                error_type="ServiceError",
                error_message=str(e)
            ))
            
            processing_time = time.time() - start_time
            
            return CompanyExtractionResponse(
                request_id=request_id,
                company_name=request.company_name,
                success=False,
                company_information=None,
                extraction_metadata=ExtractionMetadata(
                    pages_crawled=pages_crawled,
                    pages_attempted=pages_attempted,
                    extraction_time=processing_time,
                    sources_found=sources_found,
                    search_queries_used=search_queries_used,
                    extraction_mode_used=request.extraction_mode
                ),
                errors=errors,
                warnings=warnings,
                processing_time=processing_time
            )
    
    async def _discover_company_urls(
        self,
        request: CompanyInformationRequest,
        search_queries_used: List[str],
        errors: List[ExtractionError]
    ) -> List[Tuple[str, float]]:
        """
        Discover company URLs through SERP search with priority scoring.
        
        Args:
            request: Company information request
            search_queries_used: List to append used search queries
            errors: List to append any errors
            
        Returns:
            List of (URL, priority_score) tuples, sorted by priority
        """
        try:
            # Generate search queries
            queries = self._generate_search_queries(request)
            url_candidates = {}  # URL -> max_priority_score mapping
            
            # Perform searches for each query
            for query in queries[:3]:  # Limit to first 3 queries to avoid rate limits
                try:
                    search_queries_used.append(query)
                    logger.debug(f"Searching for: {query}")
                    
                    search_request = SearchRequest(
                        query=query,
                        country=request.country,
                        language=request.language,
                        page=1,  # Only search first page
                        social_platform=SocialPlatform.NONE,
                        instagram_content_type=InstagramContentType.ALL,
                        linkedin_content_type=LinkedInContentType.ALL
                    )
                    
                    search_response = await self.serp_service.search(search_request)
                    
                    # Extract URLs and score them
                    for result in search_response.organic_results[:5]:  # Top 5 results per query
                        url = str(result.url)
                        priority_score = self._score_url_priority(
                            url, result.title, result.description or "", request
                        )
                        
                        # Keep highest score for each URL
                        if url not in url_candidates or priority_score > url_candidates[url]:
                            url_candidates[url] = priority_score
                    
                    # Add delay between searches to respect rate limits
                    await asyncio.sleep(0.5)
                    
                except BrightDataError as e:
                    logger.warning(f"SERP search failed for query '{query}': {e}")
                    errors.append(ExtractionError(
                        error_type="SearchError",
                        error_message=f"Search failed for query '{query}': {str(e)}"
                    ))
                except Exception as e:
                    logger.error(f"Unexpected error during search for '{query}': {e}")
                    errors.append(ExtractionError(
                        error_type="UnexpectedError", 
                        error_message=f"Unexpected search error for '{query}': {str(e)}"
                    ))
            
            # Sort URLs by priority score (highest first) and limit results
            sorted_urls = sorted(
                url_candidates.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:request.max_pages_to_crawl]
            
            logger.info(f"Discovered {len(sorted_urls)} URLs for {request.company_name}")
            
            return sorted_urls
            
        except Exception as e:
            logger.error(f"Error in URL discovery: {e}", exc_info=True)
            errors.append(ExtractionError(
                error_type="DiscoveryError",
                error_message=f"URL discovery failed: {str(e)}"
            ))
            return []
    
    def _generate_search_queries(self, request: CompanyInformationRequest) -> List[str]:
        """
        Generate dynamic search queries for company discovery.
        
        Args:
            request: Company information request
            
        Returns:
            List of search queries optimized for different types of information
        """
        company_name = request.company_name
        queries = []
        
        # Base company information query
        if request.domain:
            queries.append(f'"{company_name}" site:{request.domain}')
        else:
            queries.append(f'"{company_name}" company information')
        
        # Mode-specific queries
        if request.extraction_mode in [ExtractionMode.COMPREHENSIVE, ExtractionMode.CONTACT_FOCUSED]:
            queries.extend([
                f'"{company_name}" contact information',
                f'"{company_name}" address phone email',
                f'"{company_name}" about us'
            ])
        
        if request.extraction_mode in [ExtractionMode.COMPREHENSIVE, ExtractionMode.FINANCIAL_FOCUSED]:
            queries.extend([
                f'"{company_name}" funding investors',
                f'"{company_name}" revenue valuation',
                f'"{company_name}" crunchbase'
            ])
        
        # Social media queries
        if request.include_social_media:
            queries.extend([
                f'"{company_name}" linkedin',
                f'"{company_name}" twitter',
                f'"{company_name}" social media'
            ])
        
        # Personnel queries
        if request.include_key_personnel:
            queries.extend([
                f'"{company_name}" CEO founder',
                f'"{company_name}" leadership team',
                f'"{company_name}" executives'
            ])
        
        return queries
    
    def _score_url_priority(
        self, 
        url: str, 
        title: str, 
        description: str, 
        request: CompanyInformationRequest
    ) -> float:
        """
        Score URL priority for crawling based on relevance to company information.
        
        Args:
            url: URL to score
            title: Page title
            description: Page description
            request: Company information request
            
        Returns:
            Priority score (0.0 to 1.0)
        """
        score = 0.0
        company_name_lower = request.company_name.lower()
        
        # Parse URL components
        try:
            parsed_url = urlparse(url.lower())
            domain = parsed_url.netloc.replace('www.', '')
            path = parsed_url.path.lower()
        except Exception:
            return 0.0
        
        # Domain scoring
        if request.domain and request.domain.lower() in domain:
            score += 0.4  # Official domain gets highest priority
        elif company_name_lower.replace(' ', '') in domain.replace('-', '').replace('_', ''):
            score += 0.3  # Company name in domain
        
        # Known high-value domains
        high_value_domains = [
            'linkedin.com', 'crunchbase.com', 'bloomberg.com', 
            'forbes.com', 'reuters.com', 'sec.gov'
        ]
        for hv_domain in high_value_domains:
            if hv_domain in domain:
                score += 0.2
                break
        
        # Path-based scoring (official site pages)
        high_value_paths = [
            'about', 'contact', 'company', 'team', 'leadership',
            'investors', 'careers', 'press', 'news'
        ]
        for hv_path in high_value_paths:
            if hv_path in path:
                score += 0.15
                break
        
        # Title scoring
        if title:
            title_lower = title.lower()
            if company_name_lower in title_lower:
                score += 0.2
            
            # Mode-specific title scoring
            if request.extraction_mode == ExtractionMode.CONTACT_FOCUSED:
                contact_keywords = ['contact', 'address', 'phone', 'email', 'location']
                for keyword in contact_keywords:
                    if keyword in title_lower:
                        score += 0.1
                        break
            
            elif request.extraction_mode == ExtractionMode.FINANCIAL_FOCUSED:
                financial_keywords = ['investor', 'funding', 'financial', 'revenue', 'valuation']
                for keyword in financial_keywords:
                    if keyword in title_lower:
                        score += 0.1
                        break
        
        # Description scoring
        if description:
            desc_lower = description.lower()
            if company_name_lower in desc_lower:
                score += 0.1
            
            # Look for company-related keywords in description
            company_keywords = [
                'company', 'business', 'corporation', 'organization',
                'startup', 'enterprise', 'firm'
            ]
            for keyword in company_keywords:
                if keyword in desc_lower:
                    score += 0.05
                    break
        
        # Penalize irrelevant domains
        irrelevant_domains = [
            'wikipedia.org', 'facebook.com', 'instagram.com', 'twitter.com',
            'youtube.com', 'pinterest.com', 'reddit.com'
        ]
        for irrelevant in irrelevant_domains:
            if irrelevant in domain:
                score *= 0.7  # Reduce score but don't eliminate
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    async def _crawl_company_pages(
        self,
        url_candidates: List[Tuple[str, float]],
        request: CompanyInformationRequest,
        errors: List[ExtractionError]
    ) -> Tuple[List[Tuple[str, str, Dict]], int, int]:
        """
        Crawl company pages with rate limiting and error handling.
        
        Args:
            url_candidates: List of (URL, priority_score) tuples
            request: Company information request
            errors: List to append crawl errors
            
        Returns:
            Tuple of (crawl_results, pages_crawled, pages_attempted)
        """
        crawl_results = []
        pages_crawled = 0
        pages_attempted = 0
        
        # Rate limiting configuration
        base_delay = 1.0  # Base delay between requests
        max_concurrent = 3  # Maximum concurrent crawl requests
        
        # Create semaphore for concurrent control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_single_url(url_info: Tuple[str, float]) -> Optional[Tuple[str, str, Dict]]:
            """Crawl a single URL with error handling."""
            nonlocal pages_attempted, pages_crawled
            url, priority_score = url_info
            
            async with semaphore:  # Limit concurrent requests
                try:
                    pages_attempted += 1
                    logger.debug(f"Crawling URL: {url} (priority: {priority_score:.2f})")
                    
                    crawl_request = CrawlRequest(
                        url=url,
                        include_raw_html=False,
                        word_count_threshold=50,
                        extraction_strategy="NoExtractionStrategy",
                        chunking_strategy="RegexChunking",
                        user_agent=None,
                        headers={}
                    )
                    
                    # Add timeout to crawl request
                    crawl_response = await asyncio.wait_for(
                        self.crawl_service.crawl(crawl_request),
                        timeout=request.timeout_seconds
                    )
                    
                    if crawl_response.success and crawl_response.result:
                        pages_crawled += 1
                        
                        # Extract content (prefer cleaned HTML, fallback to markdown)
                        content = (
                            crawl_response.result.cleaned_html or 
                            crawl_response.result.markdown or
                            ""
                        )
                        
                        if content and len(content.strip()) > 100:  # Minimum content threshold
                            logger.debug(f"Successfully crawled {url}: {len(content)} chars")
                            
                            metadata = {
                                'url': url,
                                'title': crawl_response.result.title,
                                'priority_score': priority_score,
                                'execution_time': crawl_response.execution_time,
                                'word_count': len(content.split()),
                                'metadata': crawl_response.result.metadata or {}
                            }
                            
                            return (url, content, metadata)
                        else:
                            logger.warning(f"Insufficient content from {url}")
                            errors.append(ExtractionError(
                                error_type="InsufficientContent",
                                error_message=f"Insufficient content from {url}",
                                url=url
                            ))
                    else:
                        error_msg = crawl_response.error or "Unknown crawl error"
                        logger.warning(f"Crawl failed for {url}: {error_msg}")
                        errors.append(ExtractionError(
                            error_type="CrawlError",
                            error_message=error_msg,
                            url=url
                        ))
                    
                    return None
                    
                except asyncio.TimeoutError:
                    error_msg = f"Crawl timeout after {request.timeout_seconds}s"
                    logger.warning(f"{error_msg} for {url}")
                    errors.append(ExtractionError(
                        error_type="TimeoutError",
                        error_message=error_msg,
                        url=url
                    ))
                    return None
                    
                except Exception as e:
                    error_msg = f"Crawl error: {str(e)}"
                    logger.error(f"{error_msg} for {url}", exc_info=True)
                    errors.append(ExtractionError(
                        error_type="CrawlException",
                        error_message=error_msg,
                        url=url
                    ))
                    return None
                
                finally:
                    # Rate limiting delay
                    await asyncio.sleep(base_delay)
        
        # Execute crawls with controlled concurrency
        crawl_tasks = [crawl_single_url(url_info) for url_info in url_candidates]
        
        # Wait for all crawls to complete
        results = await asyncio.gather(*crawl_tasks, return_exceptions=True)
        
        # Collect successful results
        for result in results:
            if isinstance(result, tuple) and len(result) == 3:
                crawl_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Crawl task exception: {result}")
                errors.append(ExtractionError(
                    error_type="TaskException",
                    error_message=str(result)
                ))
        
        logger.info(f"Crawl completed: {len(crawl_results)} successful, "
                   f"{pages_attempted} attempted")
        
        return crawl_results, pages_crawled, pages_attempted
    
    async def _parse_company_information(
        self,
        crawl_results: List[Tuple[str, str, Dict]],
        company_name: str,
        sources_found: List[str],
        errors: List[ExtractionError]
    ) -> Optional[CompanyInformation]:
        """
        Parse and aggregate company information from crawl results.
        
        Args:
            crawl_results: List of (url, content, metadata) tuples
            company_name: Company name for validation
            sources_found: List to append successful source URLs
            errors: List to append parsing errors
            
        Returns:
            Aggregated CompanyInformation or None if parsing fails
        """
        if not crawl_results:
            logger.warning("No crawl results to parse")
            return None
        
        try:
            # Parse information from each source
            parsed_infos = []
            
            for url, content, metadata in crawl_results:
                try:
                    logger.debug(f"Parsing content from {url}")
                    
                    # Parse company information from this source
                    company_info = self.company_parser.extract_company_information(
                        html_content=content,
                        url=url,
                        company_name=company_name
                    )
                    
                    if company_info and company_info.confidence_score > 0.1:
                        parsed_infos.append((company_info, url, metadata))
                        sources_found.append(url)
                        logger.debug(f"Successfully parsed info from {url} "
                                   f"(confidence: {company_info.confidence_score:.2f})")
                    else:
                        logger.debug(f"Low confidence parsing result from {url}")
                    
                except Exception as e:
                    error_msg = f"Parse error: {str(e)}"
                    logger.warning(f"{error_msg} for {url}")
                    errors.append(ExtractionError(
                        error_type="ParseError",
                        error_message=error_msg,
                        url=url
                    ))
            
            if not parsed_infos:
                logger.warning("No successful parsing results")
                return None
            
            # Aggregate information from multiple sources
            aggregated_info = self._aggregate_company_information(parsed_infos)
            
            logger.info(f"Company information aggregated from {len(parsed_infos)} sources "
                       f"(final confidence: {aggregated_info.confidence_score:.2f})")
            
            return aggregated_info
            
        except Exception as e:
            error_msg = f"Company information parsing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(ExtractionError(
                error_type="AggregationError",
                error_message=error_msg
            ))
            return None
    
    def _aggregate_company_information(
        self, 
        parsed_infos: List[Tuple[CompanyInformation, str, Dict]]
    ) -> CompanyInformation:
        """
        Aggregate company information from multiple sources.
        
        Args:
            parsed_infos: List of (CompanyInformation, url, metadata) tuples
            
        Returns:
            Aggregated CompanyInformation
        """
        if not parsed_infos:
            raise ValueError("No parsed information to aggregate")
        
        if len(parsed_infos) == 1:
            # Single source, return as-is
            return parsed_infos[0][0]
        
        # Multiple sources - aggregate intelligently
        # Start with highest confidence source as base
        base_info, _, _ = max(parsed_infos, key=lambda x: x[0].confidence_score)
        
        # Aggregate data from other sources
        all_social_media = []
        all_personnel = []
        all_locations = set()
        
        # Collect social media profiles (deduplicate by platform)
        social_by_platform = {}
        for info, _, _ in parsed_infos:
            for social in info.social_media:
                platform = social.platform
                if platform not in social_by_platform or social.verified:
                    social_by_platform[platform] = social
        all_social_media = list(social_by_platform.values())
        
        # Collect personnel (deduplicate by name)
        personnel_by_name = {}
        for info, _, _ in parsed_infos:
            for person in info.key_personnel:
                name_key = person.name.lower().strip()
                if name_key not in personnel_by_name:
                    personnel_by_name[name_key] = person
        all_personnel = list(personnel_by_name.values())
        
        # Collect locations
        for info, _, _ in parsed_infos:
            if info.basic_info.headquarters:
                all_locations.add(info.basic_info.headquarters)
            all_locations.update(info.basic_info.locations)
        
        # Update base info with aggregated data
        base_info.social_media = all_social_media
        base_info.key_personnel = all_personnel
        base_info.basic_info.locations = list(all_locations - {base_info.basic_info.headquarters})
        
        # Fill missing basic info from other sources (prioritize higher confidence)
        sorted_infos = sorted(parsed_infos, key=lambda x: x[0].confidence_score, reverse=True)
        
        for info, _, _ in sorted_infos[1:]:  # Skip base (already highest confidence)
            basic = info.basic_info
            contact = info.contact
            
            # Fill missing basic information
            if not base_info.basic_info.description and basic.description:
                base_info.basic_info.description = basic.description
            if not base_info.basic_info.industry and basic.industry:
                base_info.basic_info.industry = basic.industry
            if not base_info.basic_info.sector and basic.sector:
                base_info.basic_info.sector = basic.sector
            if not base_info.basic_info.founded_year and basic.founded_year:
                base_info.basic_info.founded_year = basic.founded_year
            if not base_info.basic_info.employee_count and basic.employee_count:
                base_info.basic_info.employee_count = basic.employee_count
                base_info.basic_info.company_size = basic.company_size
            
            # Fill missing contact information
            if contact:
                if not base_info.contact:
                    base_info.contact = contact
                else:
                    # Merge contact info
                    if not base_info.contact.email and contact.email:
                        base_info.contact.email = contact.email
                    if not base_info.contact.phone and contact.phone:
                        base_info.contact.phone = contact.phone
                    if not base_info.contact.address and contact.address:
                        base_info.contact.address = contact.address
                        base_info.contact.city = contact.city
                        base_info.contact.state = contact.state
                        base_info.contact.country = contact.country
                        base_info.contact.postal_code = contact.postal_code
        
        # Recalculate confidence scores based on aggregated data
        total_sources = len(parsed_infos)
        avg_confidence = sum(info.confidence_score for info, _, _ in parsed_infos) / total_sources
        
        # Boost confidence for multi-source aggregation
        aggregation_bonus = min(0.1 * (total_sources - 1), 0.3)
        base_info.confidence_score = min(avg_confidence + aggregation_bonus, 1.0)
        
        # Update data quality score
        quality_scores = [info.data_quality_score or 0.0 for info, _, _ in parsed_infos]
        base_info.data_quality_score = max(quality_scores) if quality_scores else 0.0
        
        # Update completeness score
        completeness_scores = [info.completeness_score or 0.0 for info, _, _ in parsed_infos]
        base_info.completeness_score = max(completeness_scores) if completeness_scores else 0.0
        
        return base_info
    
    async def _validate_extraction_request(self, request: CompanyInformationRequest):
        """
        Validate company extraction request.
        
        Args:
            request: Request to validate
            
        Raises:
            CompanyExtractionError: If validation fails
        """
        try:
            # Validate company name
            self.validator.validate_company_name(request.company_name, raise_on_error=True)
            
            # Validate domain if provided
            if request.domain:
                self.validator.validate_domain(request.domain, raise_on_error=True)
            
            # Validate timeout
            if request.timeout_seconds <= 0 or request.timeout_seconds > 300:
                raise CompanyExtractionError(
                    f"Invalid timeout: {request.timeout_seconds}s (must be between 1-300 seconds)",
                    "INVALID_TIMEOUT"
                )
            
            # Validate page limits
            if request.max_pages_to_crawl <= 0 or request.max_pages_to_crawl > 20:
                raise CompanyExtractionError(
                    f"Invalid page limit: {request.max_pages_to_crawl} (must be between 1-20 pages)",
                    "INVALID_PAGE_LIMIT"
                )
            
            logger.debug(f"Request validation passed for company: {request.company_name}")
            
        except CompanyExtractionError:
            raise
        except Exception as e:
            raise CompanyExtractionError(
                f"Request validation failed: {str(e)}",
                "VALIDATION_ERROR",
                {"company_name": request.company_name}
            )
    
    @resilient_operation(
        retry_config=RetryConfig(max_attempts=3, base_delay=1.0),
        circuit_breaker=serp_circuit_breaker,
        enable_recovery=True
    )
    async def _discover_company_urls_resilient(
        self,
        request: CompanyInformationRequest,
        search_queries_used: List[str],
        errors: List[ExtractionError]
    ) -> List[Tuple[str, float]]:
        """
        Resilient version of URL discovery with retry logic.
        
        Args:
            request: Company information request
            search_queries_used: List to append used search queries
            errors: List to append any errors
            
        Returns:
            List of (URL, priority_score) tuples, sorted by priority
        """
        return await self._discover_company_urls(request, search_queries_used, errors)
    
    @resilient_operation(
        retry_config=RetryConfig(max_attempts=2, base_delay=0.5),
        circuit_breaker=crawl_circuit_breaker,
        enable_recovery=True
    )
    async def _crawl_company_pages_resilient(
        self,
        url_candidates: List[Tuple[str, float]],
        request: CompanyInformationRequest,
        errors: List[ExtractionError]
    ) -> Tuple[List[Tuple[str, str, Dict]], int, int]:
        """
        Resilient version of page crawling with retry logic.
        
        Args:
            url_candidates: List of (URL, priority_score) tuples
            request: Company information request
            errors: List to append crawl errors
            
        Returns:
            Tuple of (crawl_results, pages_crawled, pages_attempted)
        """
        return await self._crawl_company_pages(url_candidates, request, errors)
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status and health information.
        
        Returns:
            Service status dictionary
        """
        try:
            status_info = {
                "status": "operational",
                "serp_service_initialized": self.serp_service is not None,
                "crawl_service_initialized": self.crawl_service is not None,
                "parser_initialized": self.company_parser is not None,
                "service_version": "1.0.0"
            }
            
            # Test service health if initialized
            if self.serp_service:
                serp_status = await self.serp_service.get_service_status()
                status_info["serp_service_status"] = serp_status.get("status", "unknown")
            
            # Add validation and resilience status
            status_info["validation_enabled"] = self.validator is not None
            status_info["circuit_breakers"] = {
                "serp_service": serp_circuit_breaker.state.value,
                "crawl_service": crawl_circuit_breaker.state.value
            }
            status_info["retry_configs"] = {
                "serp_max_attempts": self.serp_retry_config.max_attempts,
                "crawl_max_attempts": self.crawl_retry_config.max_attempts
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "service_version": "1.0.0",
                "validation_enabled": False,
                "circuit_breakers": {
                    "serp_service": "unknown",
                    "crawl_service": "unknown"
                }
            }


# Legacy alias for backward compatibility
CompanyService = CompanyExtractionService