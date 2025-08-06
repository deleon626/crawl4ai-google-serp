"""
Google SERP HTML Parser

This module provides robust parsing of Google Search Engine Results Pages (SERP)
retrieved through the Bright Data proxy service. It extracts organic search results,
metadata, and handles various Google layout variations.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag, NavigableString

from app.models.serp import SearchResponse, SearchResult, PaginationMetadata
from app.utils.pagination import PaginationHelper

# Set up logging
logger = logging.getLogger(__name__)


class GoogleSERPParser:
    """
    Production-ready Google SERP HTML parser.
    
    Handles multiple Google layout variations, extracts organic results,
    and provides comprehensive error handling and validation.
    """
    
    # CSS selectors for different Google SERP layouts (Updated 2024)
    SELECTORS = {
        # Main result containers - Updated based on real Google HTML
        'result_containers': [
            '.MjjYud',              # Primary container (2024)
            '.tF2Cxc',              # Result item container (2024)
            '#search .g',           # Fallback: Standard layout
            '.g',                   # Fallback: Generic
            '.rc',                  # Fallback: Classic layout
        ],
        
        # Title selectors - Updated based on real Google HTML
        'titles': [
            '.LC20lb',              # Primary title class (2024)
            'h3.LC20lb',            # Title with h3 tag
            '.MBeuO',               # Alternative title class
            'h3',                   # Generic fallback
            'a h3',                 # Title inside link
            '[role="heading"]',     # Accessible heading
        ],
        
        # URL selectors  
        'urls': [
            '.yuRUbf a[href]',      # Standard URL container
            'a[href]',              # Generic link
            '.r a[href]',           # Classic layout
            '[data-ved] a[href]',   # Variation
        ],
        
        # Description selectors - Updated based on real Google HTML  
        'descriptions': [
            '.VwiC3b',              # Primary description class (2024)
            '.yXK7lf',              # Alternative description
            '.p4wth',               # Another description class
            '.hJNv6b',              # Additional description class
            '.s3v9rd',              # Fallback: Alternative description  
            '.X5LH0c',              # Fallback: Another variation
            '.st',                  # Fallback: Classic snippet
            '[data-sncf]',          # Fallback: Snippet container
        ],
        
        # Metadata selectors
        'result_stats': [
            '#result-stats',        # Result count container
            '.LHJvCe',              # Alternative stats
        ]
    }
    
    # Patterns to identify and filter out non-organic results
    NON_ORGANIC_PATTERNS = [
        'shopping-carousel',
        'mnr-c',                    # Knowledge panel
        'kp-header',               # Knowledge panel header
        'g-blk',                   # Blocked results
        'ads-fr',                  # Ads
        'tads',                    # Top ads
        'bottomads',               # Bottom ads
    ]
    
    def __init__(self):
        """Initialize the parser with default configuration."""
        self.parser_name = 'html.parser'  # Use built-in parser to avoid lxml dependency
        self.pagination_helper = PaginationHelper()
        
    def parse_html(
        self, 
        html_content: str, 
        query: str, 
        current_page: int = 1,
        results_per_page: int = 10
    ) -> SearchResponse:
        """
        Parse Google SERP HTML and extract search results.
        
        Args:
            html_content: Raw HTML content from Google SERP
            query: Original search query
            current_page: Current page number for pagination metadata
            results_per_page: Expected results per page
            
        Returns:
            SearchResponse with parsed organic results and pagination metadata
        """
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content provided")
            return self._create_empty_response(query, "Empty HTML content")
            
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, self.parser_name)
            
            # Log basic HTML info for debugging
            logger.debug(f"Parsed HTML content: {len(html_content)} chars")
            
            # Extract organic results
            organic_results = self._extract_organic_results(soup, results_per_page)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, html_content)
            
            # Generate pagination metadata
            pagination_metadata = self._generate_pagination_metadata(
                current_page, results_per_page, len(organic_results), html_content
            )
            
            # Create response
            response = SearchResponse(
                query=query,
                results_count=len(organic_results),
                organic_results=organic_results,
                pagination=pagination_metadata,
                search_metadata=metadata
            )
            
            logger.info(f"Successfully parsed {len(organic_results)} results for query: {query} (page {current_page})")
            return response
            
        except Exception as e:
            logger.error(f"Error parsing HTML for query '{query}': {str(e)}", exc_info=True)
            return self._create_empty_response(query, f"Parse error: {str(e)}")
    
    def _extract_organic_results(self, soup: BeautifulSoup, max_results: int = 10) -> List[SearchResult]:
        """
        Extract organic search results from parsed HTML.
        
        Args:
            soup: BeautifulSoup parsed HTML
            max_results: Maximum number of results to extract
            
        Returns:
            List of SearchResult objects
        """
        results = []
        rank = 1
        
        # Add safety validation for excessive result requests
        if max_results > 200:
            logger.warning(f"Large result request detected: {max_results}. Consider using batch pagination.")
            max_results = 200  # Cap at reasonable limit
        
        # Try different container selectors
        containers = self._find_result_containers(soup)
        
        if not containers:
            logger.warning("No result containers found")
            return results
            
        logger.debug(f"Found {len(containers)} potential result containers")
        
        # Enhanced monitoring counters
        processing_stats = {
            'containers_processed': 0,
            'non_organic_skipped': 0,
            'missing_data_skipped': 0,
            'invalid_url_skipped': 0,
            'validation_errors': 0,
            'successful_extractions': 0
        }
        
        for container in containers:
            processing_stats['containers_processed'] += 1
            try:
                # Skip non-organic results
                if self._is_non_organic(container):
                    processing_stats['non_organic_skipped'] += 1
                    logger.debug(f"Skipping non-organic container (ads, knowledge panel, etc.)")
                    continue
                    
                # Extract result data
                title, title_elem = self._extract_title(container)
                url = self._extract_url(container, title_elem)
                description = self._extract_description(container)
                
                # Validate extracted data
                if not title or not url:
                    processing_stats['missing_data_skipped'] += 1
                    logger.debug(f"Skipping result {rank}: missing title or URL (title={bool(title)}, url={bool(url)})")
                    continue
                    
                # Validate URL format
                if not self._is_valid_url(url):
                    processing_stats['invalid_url_skipped'] += 1
                    logger.debug(f"Skipping result {rank}: invalid URL format: {url}")
                    continue
                
                # Create SearchResult
                result = SearchResult(
                    rank=rank,
                    title=title.strip(),
                    url=url,
                    description=description.strip() if description else None
                )
                
                results.append(result)
                processing_stats['successful_extractions'] += 1
                rank += 1
                
                # Limit results based on request parameters
                if rank > max_results:
                    logger.debug(f"Reached maximum results limit: {max_results}")
                    break
                    
            except Exception as e:
                processing_stats['validation_errors'] += 1
                logger.warning(f"Error processing result container {rank}: {str(e)}")
                continue
        
        # Enhanced logging for result extraction monitoring
        logger.info(f"Extracted {len(results)} valid organic results from {len(containers)} containers")
        logger.debug(f"Parser performance: {len(results)}/{max_results} requested results (extraction rate: {len(results)/max_results*100:.1f}%)")
        
        # Log detailed processing statistics
        logger.debug(f"Processing breakdown:")
        logger.debug(f"  📦 Containers processed: {processing_stats['containers_processed']}")
        logger.debug(f"  ✅ Successful extractions: {processing_stats['successful_extractions']}")
        logger.debug(f"  📢 Non-organic skipped: {processing_stats['non_organic_skipped']}")
        logger.debug(f"  ❓ Missing data skipped: {processing_stats['missing_data_skipped']}")
        logger.debug(f"  🔗 Invalid URL skipped: {processing_stats['invalid_url_skipped']}")
        logger.debug(f"  ⚠️  Validation errors: {processing_stats['validation_errors']}")
        
        # Calculate processing efficiency
        total_processed = processing_stats['containers_processed']
        if total_processed > 0:
            success_rate = processing_stats['successful_extractions'] / total_processed * 100
            logger.debug(f"Container processing efficiency: {success_rate:.1f}% success rate")
        
        # Log result distribution details
        if results:
            first_rank = results[0].rank if results else 0
            last_rank = results[-1].rank if results else 0
            logger.debug(f"Result rank range: {first_rank}-{last_rank}")
            
            # Log domain diversity for quality assessment
            domains = set()
            for result in results:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(str(result.url)).netloc
                    domains.add(domain)
                except:
                    pass
            logger.debug(f"Domain diversity: {len(domains)} unique domains in {len(results)} results")
        
        return results
    
    def _find_result_containers(self, soup: BeautifulSoup) -> List[Tag]:
        """Find result containers using multiple selector strategies."""
        containers = []
        selector_attempts = []
        
        for i, selector in enumerate(self.SELECTORS['result_containers']):
            try:
                found = soup.select(selector)
                selector_attempts.append({
                    'selector': selector,
                    'found_count': len(found),
                    'success': len(found) > 0
                })
                
                if found:
                    logger.debug(f"✅ Found {len(found)} containers with selector: {selector} (attempt {i+1})")
                    containers = found
                    break
                else:
                    logger.debug(f"❌ No containers found with selector: {selector}")
                    
            except Exception as e:
                logger.debug(f"❌ Selector '{selector}' failed: {str(e)}")
                selector_attempts.append({
                    'selector': selector,
                    'error': str(e),
                    'success': False
                })
                continue
        
        # Log selector performance summary
        successful_selectors = [s for s in selector_attempts if s.get('success', False)]
        logger.debug(f"Container detection: {len(successful_selectors)}/{len(selector_attempts)} selectors succeeded")
        
        if not containers:
            logger.warning("⚠️  No result containers found with any selector strategy")
            # Log HTML structure hints for debugging
            body_tags = soup.find_all(['div', 'section', 'article'], limit=10)
            logger.debug(f"HTML structure hint: Found {len(body_tags)} potential container tags")
        
        return containers
    
    def _is_non_organic(self, container: Tag) -> bool:
        """Check if container represents non-organic content (ads, knowledge panels, etc.)."""
        container_str = str(container).lower()
        container_classes = ' '.join(container.get('class', [])).lower()
        container_id = container.get('id', '').lower()
        
        for pattern in self.NON_ORGANIC_PATTERNS:
            if (pattern in container_str or 
                pattern in container_classes or 
                pattern in container_id):
                return True
                
        return False
    
    def _extract_title(self, container: Tag) -> Tuple[Optional[str], Optional[Tag]]:
        """Extract title from result container."""
        for selector in self.SELECTORS['titles']:
            try:
                title_elem = container.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and len(title_text) > 2:  # Basic validation
                        return title_text, title_elem
            except Exception as e:
                logger.debug(f"Title selector '{selector}' failed: {str(e)}")
                continue
        
        return None, None
    
    def _extract_url(self, container: Tag, title_elem: Optional[Tag] = None) -> Optional[str]:
        """Extract URL from result container."""
        # Try to find URL in title element first
        if title_elem:
            parent_link = title_elem.find_parent('a')
            if parent_link and parent_link.get('href'):
                href = parent_link.get('href')
                if href.startswith('http'):
                    return href
        
        # Try URL selectors
        for selector in self.SELECTORS['urls']:
            try:
                url_elem = container.select_one(selector)
                if url_elem:
                    href = url_elem.get('href')
                    if href and href.startswith('http'):
                        return href
            except Exception as e:
                logger.debug(f"URL selector '{selector}' failed: {str(e)}")
                continue
        
        return None
    
    def _extract_description(self, container: Tag) -> Optional[str]:
        """Extract description/snippet from result container."""
        for selector in self.SELECTORS['descriptions']:
            try:
                desc_elem = container.select_one(selector)
                if desc_elem:
                    # Handle multiple text nodes and clean up
                    description = desc_elem.get_text(separator=' ', strip=True)
                    if description and len(description) > 10:  # Basic validation
                        # Clean up common artifacts
                        description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
                        description = re.sub(r'^[•·\-\s]+', '', description)  # Remove bullet points
                        return description
            except Exception as e:
                logger.debug(f"Description selector '{selector}' failed: {str(e)}")
                continue
        
        return None
    
    def _extract_metadata(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Extract search metadata from the SERP."""
        metadata = {
            'parser_version': '1.0.0',
            'content_length': len(html_content),
            'parsing_method': 'beautifulsoup4'
        }
        
        # Try to extract result count
        for selector in self.SELECTORS['result_stats']:
            try:
                stats_elem = soup.select_one(selector)
                if stats_elem:
                    stats_text = stats_elem.get_text(strip=True)
                    # Extract number from text like "About 1,234,567 results"
                    match = re.search(r'([\d,]+)', stats_text)
                    if match:
                        result_count_str = match.group(1).replace(',', '')
                        try:
                            metadata['total_results'] = int(result_count_str)
                        except ValueError:
                            pass
                    metadata['result_stats_text'] = stats_text
                    break
            except Exception as e:
                logger.debug(f"Stats selector '{selector}' failed: {str(e)}")
                continue
        
        # Check for captcha or blocked content
        if 'captcha' in html_content.lower():
            metadata['captcha_detected'] = True
            
        if 'blocked' in html_content.lower() or 'unusual traffic' in html_content.lower():
            metadata['access_blocked'] = True
        
        return metadata
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ('http', 'https') and
                parsed.netloc and
                len(url) > 10 and
                not url.startswith('javascript:')
            )
        except Exception:
            return False
    
    def _generate_pagination_metadata(
        self, 
        current_page: int, 
        results_per_page: int, 
        actual_results_count: int, 
        html_content: str
    ) -> Optional[PaginationMetadata]:
        """
        Generate pagination metadata from search results and HTML content.
        
        Args:
            current_page: Current page number
            results_per_page: Expected results per page
            actual_results_count: Actual number of results found
            html_content: Raw HTML content to extract total results from
            
        Returns:
            PaginationMetadata object or None if generation fails
        """
        try:
            # Extract total results estimate from HTML content
            total_results_estimate = self.pagination_helper.extract_total_results_from_text(html_content)
            
            # Generate comprehensive pagination metadata
            pagination_metadata = self.pagination_helper.generate_pagination_metadata(
                current_page=current_page,
                results_per_page=results_per_page,
                actual_results_count=actual_results_count,
                total_results_estimate=total_results_estimate
            )
            
            logger.debug(f"Generated pagination metadata: page {current_page}, "
                        f"total estimate: {total_results_estimate}, "
                        f"actual results: {actual_results_count}")
            
            return pagination_metadata
            
        except Exception as e:
            logger.warning(f"Failed to generate pagination metadata: {str(e)}")
            return None
    
    def _create_empty_response(self, query: str, reason: str, current_page: int = 1) -> SearchResponse:
        """Create empty response with error metadata."""
        return SearchResponse(
            query=query,
            results_count=0,
            organic_results=[],
            pagination=None,
            search_metadata={
                'error': reason,
                'parser_version': '1.0.0'
            }
        )


class SERPParsingError(Exception):
    """Custom exception for SERP parsing errors."""
    pass


# Factory function for easy instantiation
def create_google_serp_parser() -> GoogleSERPParser:
    """Create and return a new GoogleSERPParser instance."""
    return GoogleSERPParser()