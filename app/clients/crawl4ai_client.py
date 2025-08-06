"""Crawl4ai client wrapper."""

import time
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from crawl4ai import AsyncWebCrawler
from crawl4ai.chunking_strategy import RegexChunking, IdentityChunking
from crawl4ai.extraction_strategy import NoExtractionStrategy, LLMExtractionStrategy
from crawl4ai.async_configs import CrawlerRunConfig

from config.settings import settings

logger = logging.getLogger(__name__)


class Crawl4aiClient:
    """Client wrapper for Crawl4ai AsyncWebCrawler."""
    
    def __init__(self):
        """Initialize Crawl4ai client."""
        self.timeout = settings.crawl4ai_timeout
        self.max_retries = settings.crawl4ai_max_retries
        self._crawler = None
    
    @asynccontextmanager
    async def _get_crawler(self):
        """Get AsyncWebCrawler instance with proper lifecycle management."""
        if self._crawler is None:
            self._crawler = AsyncWebCrawler(
                verbose=True,
                browser_type="chromium",
                headless=True,
                timeout=self.timeout * 1000,  # Convert to milliseconds
            )
        
        async with self._crawler as crawler:
            yield crawler
    
    def _get_extraction_strategy(self, strategy_name: str):
        """Get extraction strategy instance by name."""
        strategies = {
            "NoExtractionStrategy": NoExtractionStrategy(),
            "LLMExtractionStrategy": LLMExtractionStrategy(),
        }
        return strategies.get(strategy_name, NoExtractionStrategy())
    
    def _get_chunking_strategy(self, strategy_name: str):
        """Get chunking strategy instance by name."""
        strategies = {
            "RegexChunking": RegexChunking(),
            "IdentityChunking": IdentityChunking(),
        }
        return strategies.get(strategy_name, RegexChunking())
    
    async def crawl_url(
        self,
        url: str,
        include_raw_html: bool = False,
        word_count_threshold: int = 10,
        extraction_strategy: str = "NoExtractionStrategy",
        chunking_strategy: str = "RegexChunking",
        css_selector: Optional[str] = None,
        user_agent: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Crawl a URL using Crawl4ai AsyncWebCrawler.
        
        Args:
            url: URL to crawl
            include_raw_html: Include raw HTML in response
            word_count_threshold: Minimum word count threshold
            extraction_strategy: Content extraction strategy name
            chunking_strategy: Content chunking strategy name
            css_selector: CSS selector for content extraction
            user_agent: Custom user agent
            headers: Custom headers
            
        Returns:
            Dict containing crawl results
        """
        start_time = time.time()
        
        try:
            # Prepare crawler configuration
            config = CrawlerRunConfig(
                word_count_threshold=word_count_threshold,
                only_text=not include_raw_html,
                css_selector=css_selector,
                user_agent=user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                headers=headers or {},
                extraction_strategy=self._get_extraction_strategy(extraction_strategy),
                chunking_strategy=self._get_chunking_strategy(chunking_strategy)
            )
            
            # Perform crawling
            async with self._get_crawler() as crawler:
                logger.info(f"Crawling URL: {url}")
                result = await crawler.arun(
                    url=url,
                    config=config
                )
                
                if not result.success:
                    logger.error(f"Crawl failed for {url}: {result.error}")
                    return {
                        "success": False,
                        "url": url,
                        "result": None,
                        "error": result.error or "Unknown crawl error",
                        "execution_time": time.time() - start_time,
                        "config": {
                            "url": url,
                            "include_raw_html": include_raw_html,
                            "word_count_threshold": word_count_threshold,
                            "extraction_strategy": extraction_strategy,
                            "chunking_strategy": chunking_strategy,
                            "css_selector": css_selector,
                            "user_agent": user_agent,
                            "headers": headers or {}
                        }
                    }
                
                # Extract relevant data from crawl result
                crawl_data = {
                    "url": result.url,
                    "title": getattr(result, 'title', None),
                    "markdown": getattr(result, 'markdown', None),
                    "cleaned_html": getattr(result, 'cleaned_html', None) if include_raw_html else None,
                    "media": {
                        "images": getattr(result, 'images', []),
                        "videos": getattr(result, 'videos', []),
                    },
                    "links": {
                        "internal": getattr(result, 'internal_links', []),
                        "external": getattr(result, 'external_links', []),
                    },
                    "metadata": {
                        "word_count": len(result.markdown.split()) if result.markdown else 0,
                        "extracted_content": getattr(result, 'extracted_content', None),
                        "status_code": getattr(result, 'status_code', None),
                        "response_headers": getattr(result, 'response_headers', {}),
                    }
                }
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully crawled {url} in {execution_time:.2f}s")
                
                return {
                    "success": True,
                    "url": url,
                    "result": crawl_data,
                    "error": None,
                    "execution_time": execution_time,
                    "config": {
                        "url": url,
                        "include_raw_html": include_raw_html,
                        "word_count_threshold": word_count_threshold,
                        "extraction_strategy": extraction_strategy,
                        "chunking_strategy": chunking_strategy,
                        "css_selector": css_selector,
                        "user_agent": user_agent,
                        "headers": headers or {}
                    }
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Crawl4ai error for {url}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "url": url,
                "result": None,
                "error": error_msg,
                "execution_time": execution_time,
                "config": {
                    "url": url,
                    "include_raw_html": include_raw_html,
                    "word_count_threshold": word_count_threshold,
                    "extraction_strategy": extraction_strategy,
                    "chunking_strategy": chunking_strategy,
                    "css_selector": css_selector,
                    "user_agent": user_agent,
                    "headers": headers or {}
                }
            }