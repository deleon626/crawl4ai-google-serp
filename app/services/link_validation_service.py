"""Link extraction and validation service."""

import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, unquote
from dataclasses import dataclass
import aiohttp
import time

logger = logging.getLogger(__name__)


@dataclass
class LinkInfo:
    """Information about an extracted link."""
    url: str
    original_text: str
    link_type: str  # website, social, email, phone, other
    domain: str
    is_business_link: bool
    confidence: float
    validation_status: Optional[str] = None  # valid, invalid, timeout, error
    response_time: Optional[float] = None
    status_code: Optional[int] = None


class LinkExtractor:
    """Extract and categorize links from text content."""
    
    def __init__(self):
        """Initialize link extractor with patterns."""
        self.url_patterns = self._compile_url_patterns()
        self.social_domains = self._get_social_media_domains()
        self.business_domains = self._get_business_domains()
    
    def _compile_url_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for different types of links."""
        patterns = {
            "http_url": re.compile(
                r'https?://(?:[-\w.])+(?::\d+)?(?:/[^\s]*)?', 
                re.IGNORECASE
            ),
            "www_url": re.compile(
                r'www\.(?:[-\w.])+(?::\d+)?(?:/[^\s]*)?', 
                re.IGNORECASE
            ),
            "domain_only": re.compile(
                r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?\b', 
                re.IGNORECASE
            ),
            "email": re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                re.IGNORECASE
            ),
            "phone": re.compile(
                r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', 
                re.IGNORECASE
            ),
            "social_handle": re.compile(
                r'@[a-zA-Z0-9_]+', 
                re.IGNORECASE
            ),
            "link_in_bio": re.compile(
                r'(link\s+in\s+bio|linkinbio|bio\s+link)', 
                re.IGNORECASE
            )
        }
        return patterns
    
    def _get_social_media_domains(self) -> Set[str]:
        """Get set of social media domains."""
        return {
            "instagram.com", "facebook.com", "twitter.com", "x.com", "linkedin.com",
            "tiktok.com", "youtube.com", "snapchat.com", "pinterest.com",
            "whatsapp.com", "telegram.org", "t.me", "wa.me", "fb.me",
            "bit.ly", "tinyurl.com", "t.co"  # URL shorteners often used for social
        }
    
    def _get_business_domains(self) -> Set[str]:
        """Get set of known business/e-commerce domains."""
        return {
            "shopify.com", "etsy.com", "amazon.com", "square.com", "squarespace.com",
            "wix.com", "wordpress.com", "weebly.com", "godaddy.com", "bigcommerce.com",
            "stripe.com", "paypal.com", "venmo.com", "cashapp.com", "zelle.com"
        }
    
    def extract_links_from_text(self, text: str) -> List[LinkInfo]:
        """
        Extract and categorize all links from text.
        
        Args:
            text: Text content to extract links from
            
        Returns:
            List of LinkInfo objects with extracted link data
        """
        if not text:
            return []
        
        links = []
        processed_urls = set()  # Avoid duplicates
        
        # Extract HTTP URLs
        for match in self.url_patterns["http_url"].finditer(text):
            url = match.group(0)
            if url not in processed_urls:
                links.append(self._create_link_info(url, url, "http_url"))
                processed_urls.add(url)
        
        # Extract www URLs (add http://)
        for match in self.url_patterns["www_url"].finditer(text):
            original = match.group(0)
            url = f"http://{original}"
            if url not in processed_urls:
                links.append(self._create_link_info(url, original, "www_url"))
                processed_urls.add(url)
        
        # Extract domain-only URLs (excluding those already found)
        for match in self.url_patterns["domain_only"].finditer(text):
            original = match.group(0)
            # Skip if already found as HTTP or www URL
            if any(original in existing for existing in processed_urls):
                continue
            url = f"http://{original}"
            if url not in processed_urls:
                links.append(self._create_link_info(url, original, "domain_only"))
                processed_urls.add(url)
        
        # Extract emails
        for match in self.url_patterns["email"].finditer(text):
            email = match.group(0)
            if email not in processed_urls:
                links.append(self._create_link_info(f"mailto:{email}", email, "email"))
                processed_urls.add(email)
        
        # Extract phone numbers
        for match in self.url_patterns["phone"].finditer(text):
            phone = match.group(0)
            if phone not in processed_urls:
                links.append(self._create_link_info(f"tel:{phone}", phone, "phone"))
                processed_urls.add(phone)
        
        logger.debug(f"Extracted {len(links)} links from text")
        return links
    
    def _create_link_info(self, url: str, original_text: str, pattern_type: str) -> LinkInfo:
        """Create LinkInfo object with analysis."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix for domain comparison
            clean_domain = domain.replace("www.", "")
            
            # Determine link type
            link_type = self._classify_link_type(clean_domain, url, pattern_type)
            
            # Assess business relevance
            is_business_link, confidence = self._assess_business_relevance(
                clean_domain, url, original_text, link_type
            )
            
            return LinkInfo(
                url=url,
                original_text=original_text,
                link_type=link_type,
                domain=clean_domain,
                is_business_link=is_business_link,
                confidence=confidence
            )
            
        except Exception as e:
            logger.warning(f"Error creating link info for {url}: {e}")
            return LinkInfo(
                url=url,
                original_text=original_text,
                link_type="unknown",
                domain="unknown",
                is_business_link=False,
                confidence=0.0
            )
    
    def _classify_link_type(self, domain: str, url: str, pattern_type: str) -> str:
        """Classify the type of link."""
        if pattern_type == "email":
            return "email"
        elif pattern_type == "phone":
            return "phone"
        elif domain in self.social_domains:
            return "social"
        elif domain in self.business_domains:
            return "business_platform"
        elif any(keyword in url.lower() for keyword in ["shop", "store", "buy", "order", "cart"]):
            return "e_commerce"
        elif any(keyword in url.lower() for keyword in ["book", "appointment", "schedule", "reserve"]):
            return "booking"
        else:
            return "website"
    
    def _assess_business_relevance(
        self, domain: str, url: str, original_text: str, link_type: str
    ) -> Tuple[bool, float]:
        """Assess if link is business-relevant and confidence score."""
        confidence = 0.0
        
        # High business relevance
        if link_type in ["email", "phone"]:
            confidence = 0.9
        elif link_type in ["booking", "e_commerce"]:
            confidence = 0.85
        elif link_type == "business_platform":
            confidence = 0.8
        elif link_type == "social":
            # Social links can be business relevant but lower confidence
            confidence = 0.4
        else:
            # Regular websites - check for business indicators
            business_keywords = [
                "contact", "about", "services", "portfolio", "shop", "store",
                "appointment", "booking", "order", "buy", "hire", "work"
            ]
            
            url_lower = url.lower()
            text_lower = original_text.lower()
            
            for keyword in business_keywords:
                if keyword in url_lower or keyword in text_lower:
                    confidence += 0.15
            
            # Domain-based scoring
            if any(term in domain for term in ["business", "shop", "store", "pro", "official"]):
                confidence += 0.2
        
        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        is_business = confidence > 0.3
        
        return is_business, confidence


class LinkValidator:
    """Validate links by checking accessibility and response."""
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 5):
        """Initialize link validator."""
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def validate_links(self, links: List[LinkInfo]) -> List[LinkInfo]:
        """
        Validate list of links concurrently.
        
        Args:
            links: List of LinkInfo objects to validate
            
        Returns:
            List of LinkInfo objects with validation results
        """
        if not self.session:
            raise RuntimeError("LinkValidator must be used as async context manager")
        
        # Only validate web links (not email/phone)
        web_links = [link for link in links if link.link_type not in ["email", "phone"]]
        other_links = [link for link in links if link.link_type in ["email", "phone"]]
        
        # Validate web links concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._validate_single_link(link, semaphore) for link in web_links]
        
        validated_web_links = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_web_links = []
        for i, result in enumerate(validated_web_links):
            if isinstance(result, Exception):
                logger.error(f"Link validation error: {result}")
                web_links[i].validation_status = "error"
                final_web_links.append(web_links[i])
            else:
                final_web_links.append(result)
        
        # Combine results
        all_validated = final_web_links + other_links
        logger.info(f"Validated {len(final_web_links)} web links, {len(other_links)} other links")
        
        return all_validated
    
    async def _validate_single_link(self, link: LinkInfo, semaphore: asyncio.Semaphore) -> LinkInfo:
        """Validate a single link."""
        async with semaphore:
            start_time = time.time()
            
            try:
                async with self.session.head(link.url, allow_redirects=True) as response:
                    link.status_code = response.status
                    link.response_time = time.time() - start_time
                    
                    if 200 <= response.status < 300:
                        link.validation_status = "valid"
                    elif 300 <= response.status < 400:
                        link.validation_status = "redirect"
                    elif response.status == 404:
                        link.validation_status = "not_found"
                    elif response.status >= 500:
                        link.validation_status = "server_error"
                    else:
                        link.validation_status = "client_error"
                        
            except asyncio.TimeoutError:
                link.validation_status = "timeout"
                link.response_time = time.time() - start_time
            except Exception as e:
                logger.debug(f"Link validation error for {link.url}: {e}")
                link.validation_status = "error"
                link.response_time = time.time() - start_time
            
            return link


class LinkValidationService:
    """Main service for link extraction and validation."""
    
    def __init__(self, timeout: int = 10):
        """Initialize link validation service."""
        self.extractor = LinkExtractor()
        self.timeout = timeout
    
    async def extract_and_validate_links(
        self, 
        text: str, 
        validate_links: bool = True
    ) -> Dict[str, Any]:
        """
        Extract links from text and optionally validate them.
        
        Args:
            text: Text content to extract links from
            validate_links: Whether to validate link accessibility
            
        Returns:
            Dict with extracted and validated link information
        """
        # Extract links
        links = self.extractor.extract_links_from_text(text)
        
        # Validate links if requested
        if validate_links and links:
            async with LinkValidator(timeout=self.timeout) as validator:
                links = await validator.validate_links(links)
        
        # Categorize results
        result = {
            "total_links": len(links),
            "business_links": [link for link in links if link.is_business_link],
            "social_links": [link for link in links if link.link_type == "social"],
            "contact_links": [link for link in links if link.link_type in ["email", "phone"]],
            "website_links": [link for link in links if link.link_type == "website"],
            "all_links": links,
            "summary": {
                "business_count": len([link for link in links if link.is_business_link]),
                "social_count": len([link for link in links if link.link_type == "social"]),
                "contact_count": len([link for link in links if link.link_type in ["email", "phone"]]),
                "website_count": len([link for link in links if link.link_type == "website"]),
                "validated_count": len([link for link in links if link.validation_status]) if validate_links else 0,
                "valid_count": len([link for link in links if link.validation_status == "valid"]) if validate_links else 0
            }
        }
        
        logger.info(f"Extracted {result['total_links']} links, {result['summary']['business_count']} business-relevant")
        return result