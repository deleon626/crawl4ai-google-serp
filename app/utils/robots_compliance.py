"""
Robots.txt compliance and respectful crawling utilities.

This module ensures compliance with robots.txt directives and implements
respectful crawling practices to maintain ethical web scraping standards.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


class RobotsDirective(BaseModel):
    """Robots.txt directive information."""
    
    user_agent: str = Field(description="User agent the directive applies to")
    allowed: bool = Field(description="Whether the path is allowed")
    path: str = Field(description="URL path or pattern")
    crawl_delay: Optional[float] = Field(default=None, description="Crawl delay in seconds")


class SitemapInfo(BaseModel):
    """Sitemap information extracted from robots.txt."""
    
    url: str = Field(description="Sitemap URL")
    last_checked: Optional[datetime] = Field(default=None, description="Last time sitemap was checked")
    priority_urls: List[str] = Field(default_factory=list, description="High-priority URLs from sitemap")


class RobotsCache(BaseModel):
    """Cached robots.txt information."""
    
    domain: str = Field(description="Domain name")
    robots_content: str = Field(description="Raw robots.txt content")
    directives: List[RobotsDirective] = Field(description="Parsed directives")
    sitemaps: List[SitemapInfo] = Field(description="Available sitemaps")
    crawl_delay: float = Field(description="Global crawl delay for domain")
    last_updated: datetime = Field(description="Last time robots.txt was fetched")
    expires_at: datetime = Field(description="Cache expiration time")


class CrawlTracker:
    """Track crawling activity for rate limiting compliance."""
    
    def __init__(self):
        self.last_crawl_times: Dict[str, datetime] = {}
        self.crawl_counts: Dict[str, int] = {}
        self.reset_times: Dict[str, datetime] = {}
        self.blocked_domains: Set[str] = set()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.current_user_agent_index = 0
    
    def get_user_agent(self) -> str:
        """Get next user agent in rotation."""
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        return user_agent
    
    def can_crawl(self, domain: str, required_delay: float = 1.0) -> bool:
        """Check if domain can be crawled respecting delays."""
        if domain in self.blocked_domains:
            return False
        
        last_crawl = self.last_crawl_times.get(domain)
        if last_crawl:
            time_since = (datetime.utcnow() - last_crawl).total_seconds()
            return time_since >= required_delay
        
        return True
    
    def record_crawl(self, domain: str):
        """Record successful crawl attempt."""
        now = datetime.utcnow()
        self.last_crawl_times[domain] = now
        self.crawl_counts[domain] = self.crawl_counts.get(domain, 0) + 1
        
        # Reset hourly counts
        if domain not in self.reset_times or (now - self.reset_times[domain]).seconds >= 3600:
            self.crawl_counts[domain] = 1
            self.reset_times[domain] = now
    
    def block_domain(self, domain: str, duration_hours: int = 24):
        """Temporarily block domain for excessive requests."""
        self.blocked_domains.add(domain)
        logger.warning(f"Temporarily blocked domain {domain} for {duration_hours} hours")
        
        # Schedule unblocking (in production, use Redis/database for persistence)
        asyncio.create_task(self._unblock_domain_later(domain, duration_hours))
    
    async def _unblock_domain_later(self, domain: str, hours: int):
        """Unblock domain after specified time."""
        await asyncio.sleep(hours * 3600)
        self.blocked_domains.discard(domain)
        logger.info(f"Unblocked domain {domain}")


class RobotsComplianceManager:
    """Manage robots.txt compliance and respectful crawling."""
    
    def __init__(self):
        self.robots_cache: Dict[str, RobotsCache] = {}
        self.crawl_tracker = CrawlTracker()
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache_duration = timedelta(hours=24)  # Cache robots.txt for 24 hours
        self.min_crawl_delay = 1.0  # Minimum delay between requests (seconds)
        self.max_requests_per_hour = 100  # Maximum requests per domain per hour
        self.respect_crawl_delay = True
        self.default_user_agent = "Crawl4AI-GoogleSERP/1.0 (respectful crawler)"
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": self.default_user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _get_robots_url(self, url: str) -> str:
        """Get robots.txt URL for domain."""
        domain = self._get_domain(url)
        return urljoin(domain, "/robots.txt")
    
    async def _fetch_robots_txt(self, domain: str) -> Optional[str]:
        """Fetch robots.txt content from domain."""
        robots_url = self._get_robots_url(domain)
        
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"Successfully fetched robots.txt from {domain}")
                    return content
                elif response.status == 404:
                    logger.info(f"No robots.txt found for {domain}")
                    return ""
                else:
                    logger.warning(f"Unexpected status {response.status} for robots.txt from {domain}")
                    return None
        
        except Exception as e:
            logger.error(f"Failed to fetch robots.txt from {domain}: {e}")
            return None
    
    def _parse_robots_txt(self, domain: str, content: str) -> Tuple[List[RobotsDirective], List[SitemapInfo], float]:
        """Parse robots.txt content."""
        directives = []
        sitemaps = []
        global_crawl_delay = self.min_crawl_delay
        
        # Use stdlib robotparser for basic parsing
        rp = RobotFileParser()
        rp.read_data(content)
        
        # Parse sitemaps
        sitemap_lines = [line.strip() for line in content.split('\n') 
                        if line.strip().lower().startswith('sitemap:')]
        
        for line in sitemap_lines:
            sitemap_url = line.split(':', 1)[1].strip()
            sitemaps.append(SitemapInfo(url=sitemap_url))
        
        # Parse crawl delays and other directives
        lines = content.split('\n')
        current_user_agent = '*'
        
        for line in lines:
            line = line.strip().lower()
            
            if line.startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            
            elif line.startswith('crawl-delay:'):
                try:
                    delay = float(line.split(':', 1)[1].strip())
                    global_crawl_delay = max(global_crawl_delay, delay)
                except ValueError:
                    pass
            
            elif line.startswith('allow:'):
                path = line.split(':', 1)[1].strip()
                directives.append(RobotsDirective(
                    user_agent=current_user_agent,
                    allowed=True,
                    path=path
                ))
            
            elif line.startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                directives.append(RobotsDirective(
                    user_agent=current_user_agent,
                    allowed=False,
                    path=path
                ))
        
        return directives, sitemaps, global_crawl_delay
    
    async def _get_robots_info(self, url: str) -> Optional[RobotsCache]:
        """Get robots.txt information for URL, using cache if available."""
        domain = self._get_domain(url)
        
        # Check cache first
        cached = self.robots_cache.get(domain)
        if cached and datetime.utcnow() < cached.expires_at:
            return cached
        
        # Fetch fresh robots.txt
        content = await self._fetch_robots_txt(domain)
        if content is None:
            return None
        
        # Parse content
        directives, sitemaps, crawl_delay = self._parse_robots_txt(domain, content)
        
        # Create cache entry
        robots_info = RobotsCache(
            domain=domain,
            robots_content=content,
            directives=directives,
            sitemaps=sitemaps,
            crawl_delay=crawl_delay,
            last_updated=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.cache_duration
        )
        
        self.robots_cache[domain] = robots_info
        return robots_info
    
    async def can_fetch(self, url: str, user_agent: str = None) -> Tuple[bool, str]:
        """
        Check if URL can be fetched according to robots.txt.
        
        Returns:
            Tuple of (can_fetch: bool, reason: str)
        """
        if not user_agent:
            user_agent = self.default_user_agent
        
        domain = self._get_domain(url)
        parsed_url = urlparse(url)
        path = parsed_url.path or '/'
        
        # Get robots information
        robots_info = await self._get_robots_info(url)
        if not robots_info:
            return True, "No robots.txt found, allowing access"
        
        # Check if explicitly allowed
        for directive in robots_info.directives:
            if directive.user_agent in ('*', user_agent) and directive.allowed:
                if path.startswith(directive.path):
                    return True, f"Explicitly allowed by robots.txt for {directive.user_agent}"
        
        # Check if explicitly disallowed
        for directive in robots_info.directives:
            if directive.user_agent in ('*', user_agent) and not directive.allowed:
                if directive.path == '' or path.startswith(directive.path):
                    return False, f"Disallowed by robots.txt for {directive.user_agent}"
        
        return True, "No matching robots.txt directive, allowing access"
    
    async def get_crawl_delay(self, url: str) -> float:
        """Get appropriate crawl delay for domain."""
        robots_info = await self._get_robots_info(url)
        
        if robots_info and self.respect_crawl_delay:
            return max(robots_info.crawl_delay, self.min_crawl_delay)
        
        return self.min_crawl_delay
    
    async def can_crawl_now(self, url: str) -> Tuple[bool, str, float]:
        """
        Check if URL can be crawled now considering timing constraints.
        
        Returns:
            Tuple of (can_crawl: bool, reason: str, delay_needed: float)
        """
        domain = self._get_domain(url)
        
        # Check if domain is temporarily blocked
        if domain in self.crawl_tracker.blocked_domains:
            return False, "Domain temporarily blocked due to excessive requests", 0
        
        # Check robots.txt compliance
        can_fetch, fetch_reason = await self.can_fetch(url)
        if not can_fetch:
            return False, fetch_reason, 0
        
        # Check timing constraints
        required_delay = await self.get_crawl_delay(url)
        can_crawl_timing = self.crawl_tracker.can_crawl(domain, required_delay)
        
        if not can_crawl_timing:
            last_crawl = self.crawl_tracker.last_crawl_times.get(domain)
            if last_crawl:
                elapsed = (datetime.utcnow() - last_crawl).total_seconds()
                remaining_delay = required_delay - elapsed
                return False, f"Must wait {remaining_delay:.1f}s before next crawl", remaining_delay
        
        # Check hourly rate limits
        hourly_count = self.crawl_tracker.crawl_counts.get(domain, 0)
        if hourly_count >= self.max_requests_per_hour:
            return False, "Hourly rate limit exceeded", 3600  # Wait an hour
        
        return True, "OK to crawl", 0
    
    async def record_successful_crawl(self, url: str):
        """Record successful crawl for rate limiting."""
        domain = self._get_domain(url)
        self.crawl_tracker.record_crawl(domain)
        logger.debug(f"Recorded successful crawl for {domain}")
    
    async def record_failed_crawl(self, url: str, status_code: int = None):
        """Record failed crawl attempt."""
        domain = self._get_domain(url)
        
        # Block domain for certain error codes
        if status_code in (429, 503):  # Rate limited or service unavailable
            self.crawl_tracker.block_domain(domain, 24)
        elif status_code in (403, 401):  # Forbidden or unauthorized
            self.crawl_tracker.block_domain(domain, 1)
        
        logger.warning(f"Recorded failed crawl for {domain} (status: {status_code})")
    
    async def get_sitemaps(self, url: str) -> List[SitemapInfo]:
        """Get available sitemaps for domain."""
        robots_info = await self._get_robots_info(url)
        return robots_info.sitemaps if robots_info else []
    
    def get_respectful_user_agent(self) -> str:
        """Get next user agent for rotation."""
        return self.crawl_tracker.get_user_agent()
    
    async def wait_if_needed(self, url: str):
        """Wait if needed before crawling URL."""
        can_crawl, reason, delay = await self.can_crawl_now(url)
        
        if not can_crawl and delay > 0:
            logger.info(f"Waiting {delay:.1f}s before crawling {url}: {reason}")
            await asyncio.sleep(delay)
        elif not can_crawl:
            raise ValueError(f"Cannot crawl {url}: {reason}")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring."""
        total_domains = len(self.robots_cache)
        expired_domains = sum(1 for cache in self.robots_cache.values() 
                            if datetime.utcnow() >= cache.expires_at)
        
        return {
            "total_cached_domains": total_domains,
            "expired_cache_entries": expired_domains,
            "blocked_domains": len(self.crawl_tracker.blocked_domains),
            "tracked_domains": len(self.crawl_tracker.last_crawl_times),
            "cache_hit_rate": (total_domains - expired_domains) / max(total_domains, 1)
        }


# Global instance
robots_manager = RobotsComplianceManager()


async def check_robots_compliance(url: str, user_agent: str = None) -> Tuple[bool, str]:
    """
    Convenience function to check robots.txt compliance.
    
    Args:
        url: URL to check
        user_agent: User agent string (optional)
    
    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    async with RobotsComplianceManager() as manager:
        return await manager.can_fetch(url, user_agent)


async def respectful_crawl_delay(url: str) -> float:
    """
    Get respectful crawl delay for URL.
    
    Args:
        url: URL to get delay for
    
    Returns:
        Delay in seconds
    """
    async with RobotsComplianceManager() as manager:
        return await manager.get_crawl_delay(url)