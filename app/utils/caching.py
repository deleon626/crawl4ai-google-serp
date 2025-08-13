"""Redis caching system for company extraction with intelligent cache management."""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import asdict
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from config.settings import settings
from app.models.company import CompanyInformation, CompanyExtractionResponse
from app.models.serp import SearchResponse

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Intelligent cache key generation for different data types."""
    
    @staticmethod
    def company_info_key(company_name: str, domain: Optional[str] = None, extraction_mode: str = "standard") -> str:
        """Generate cache key for company information."""
        key_parts = [company_name.lower().strip()]
        if domain:
            key_parts.append(domain.lower())
        key_parts.append(extraction_mode.lower())
        
        # Create hash for consistent key length
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"company:{key_hash}"
    
    @staticmethod
    def serp_results_key(query: str, country: str, language: str, page: int = 1) -> str:
        """Generate cache key for SERP results."""
        key_parts = [query.lower().strip(), country.lower(), language.lower(), str(page)]
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"serp:{key_hash}"
    
    @staticmethod
    def crawl_content_key(url: str) -> str:
        """Generate cache key for crawled content."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"crawl:{url_hash}"
    
    @staticmethod
    def batch_company_key(company_names: List[str], extraction_mode: str = "standard") -> str:
        """Generate cache key for batch company extraction."""
        sorted_names = sorted([name.lower().strip() for name in company_names])
        key_string = "|".join(sorted_names) + f"|{extraction_mode.lower()}"
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"batch:{key_hash}"


class CacheManager:
    """Redis cache manager with TTL policies and memory optimization."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager."""
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[Redis] = None
        self._connected = False
        
        # Cache TTL policies (in seconds)
        self.ttl_policies = {
            "company": 24 * 3600,      # 24 hours - company info changes slowly
            "serp": 6 * 3600,          # 6 hours - SERP results change moderately  
            "crawl": 12 * 3600,        # 12 hours - web content changes moderately
            "batch": 6 * 3600,         # 6 hours - batch results
            "performance": 300,        # 5 minutes - performance metrics
            "default": 3600            # 1 hour - default TTL
        }
        
        logger.info(f"CacheManager initialized with Redis URL: {self.redis_url}")
    
    async def connect(self) -> bool:
        """Connect to Redis server."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            
            logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis server."""
        if self._redis:
            try:
                await self._redis.aclose()
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {e}")
            finally:
                self._redis = None
                self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self._redis is not None
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active."""
        if not self.is_connected():
            return await self.connect()
        
        try:
            # Test connection health
            await self._redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection health check failed: {e}")
            self._connected = False
            return await self.connect()
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        cache_type: str = "default"
    ) -> bool:
        """Set value in cache with TTL."""
        if not await self._ensure_connection():
            logger.warning("Cache set failed - Redis not available")
            return False
        
        try:
            # Determine TTL
            if ttl is None:
                ttl = self.ttl_policies.get(cache_type, self.ttl_policies["default"])
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            elif hasattr(value, 'dict'):  # Pydantic models
                serialized_value = json.dumps(value.dict(), default=str)
            else:
                serialized_value = str(value)
            
            # Set with TTL
            success = await self._redis.setex(key, ttl, serialized_value)
            
            if success:
                logger.debug(f"Cached key: {key} (TTL: {ttl}s)")
                return True
            else:
                logger.warning(f"Failed to cache key: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not await self._ensure_connection():
            logger.debug("Cache get failed - Redis not available")
            return None
        
        try:
            value = await self._redis.get(key)
            
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            # Try to deserialize as JSON
            try:
                deserialized = json.loads(value)
                logger.debug(f"Cache hit: {key}")
                return deserialized
            except json.JSONDecodeError:
                # Return as string if not JSON
                logger.debug(f"Cache hit (string): {key}")
                return value
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not await self._ensure_connection():
            return False
        
        try:
            result = await self._redis.delete(key)
            logger.debug(f"Cache delete: {key} (existed: {result > 0})")
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not await self._ensure_connection():
            return False
        
        try:
            result = await self._redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for a key (-1 if no TTL, -2 if key doesn't exist)."""
        if not await self._ensure_connection():
            return -2
        
        try:
            ttl = await self._redis.ttl(key)
            return ttl
        except Exception as e:
            logger.error(f"Cache TTL check error for key {key}: {e}")
            return -2
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not await self._ensure_connection():
            return 0
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache pattern clear error for pattern {pattern}: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not await self._ensure_connection():
            return {"status": "disconnected"}
        
        try:
            info = await self._redis.info()
            
            stats = {
                "status": "connected",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": 0.0
            }
            
            # Calculate hit rate
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            if total > 0:
                stats["hit_rate"] = round((hits / total) * 100, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}


class CacheWarmer:
    """Cache warming strategies for popular companies and search patterns."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.popular_companies = [
            "OpenAI", "Google", "Microsoft", "Apple", "Amazon", 
            "Meta", "Tesla", "Netflix", "Uber", "Airbnb"
        ]
        logger.info("CacheWarmer initialized")
    
    async def warm_popular_companies(self, extraction_mode: str = "standard") -> Dict[str, bool]:
        """Warm cache for popular companies (placeholder - would integrate with extraction service)."""
        results = {}
        
        logger.info(f"Starting cache warming for {len(self.popular_companies)} popular companies")
        
        for company in self.popular_companies:
            try:
                cache_key = CacheKeyGenerator.company_info_key(company, extraction_mode=extraction_mode)
                
                # Check if already cached
                if await self.cache.exists(cache_key):
                    results[company] = True
                    logger.debug(f"Company {company} already cached")
                    continue
                
                # In real implementation, would extract company info here
                # For now, just mark as needing warming
                results[company] = False
                logger.debug(f"Company {company} needs cache warming")
                
                # Small delay to avoid overwhelming services
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Cache warming failed for {company}: {e}")
                results[company] = False
        
        warmed_count = sum(1 for result in results.values() if result)
        logger.info(f"Cache warming completed: {warmed_count}/{len(self.popular_companies)} already cached")
        
        return results
    
    async def warm_search_patterns(self, queries: List[str], country: str = "US", language: str = "en") -> Dict[str, bool]:
        """Warm cache for common search patterns."""
        results = {}
        
        logger.info(f"Starting cache warming for {len(queries)} search patterns")
        
        for query in queries:
            try:
                cache_key = CacheKeyGenerator.serp_results_key(query, country, language)
                
                # Check if already cached
                if await self.cache.exists(cache_key):
                    results[query] = True
                    logger.debug(f"Query '{query}' already cached")
                else:
                    results[query] = False
                    logger.debug(f"Query '{query}' needs cache warming")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Cache warming failed for query '{query}': {e}")
                results[query] = False
        
        return results


class CompanyCacheService:
    """High-level company-specific caching service."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """Initialize company cache service."""
        self.cache = cache_manager or CacheManager()
        self.cache_warmer = CacheWarmer(self.cache)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0
        }
        logger.info("CompanyCacheService initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.cache.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cache.disconnect()
    
    async def get_company_info(
        self, 
        company_name: str, 
        domain: Optional[str] = None,
        extraction_mode: str = "standard"
    ) -> Optional[Dict[str, Any]]:
        """Get cached company information."""
        cache_key = CacheKeyGenerator.company_info_key(company_name, domain, extraction_mode)
        
        try:
            result = await self.cache.get(cache_key)
            
            if result:
                self._stats["hits"] += 1
                logger.debug(f"Company cache hit for: {company_name}")
                return result
            else:
                self._stats["misses"] += 1
                logger.debug(f"Company cache miss for: {company_name}")
                return None
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Company cache get error for {company_name}: {e}")
            return None
    
    async def set_company_info(
        self,
        company_name: str,
        company_info: Union[CompanyInformation, Dict[str, Any]],
        domain: Optional[str] = None,
        extraction_mode: str = "standard",
        ttl: Optional[int] = None
    ) -> bool:
        """Cache company information."""
        cache_key = CacheKeyGenerator.company_info_key(company_name, domain, extraction_mode)
        
        try:
            # Convert to dict if Pydantic model
            if hasattr(company_info, 'dict'):
                cache_data = company_info.dict()
            else:
                cache_data = company_info
            
            # Add cache metadata
            cache_data["_cached_at"] = datetime.utcnow().isoformat()
            cache_data["_cache_key"] = cache_key
            
            success = await self.cache.set(cache_key, cache_data, ttl=ttl, cache_type="company")
            
            if success:
                self._stats["sets"] += 1
                logger.debug(f"Company info cached for: {company_name}")
                return True
            else:
                self._stats["errors"] += 1
                return False
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Company cache set error for {company_name}: {e}")
            return False
    
    async def get_serp_results(
        self,
        query: str,
        country: str,
        language: str,
        page: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get cached SERP results."""
        cache_key = CacheKeyGenerator.serp_results_key(query, country, language, page)
        
        try:
            result = await self.cache.get(cache_key)
            
            if result:
                self._stats["hits"] += 1
                logger.debug(f"SERP cache hit for query: {query}")
                return result
            else:
                self._stats["misses"] += 1
                logger.debug(f"SERP cache miss for query: {query}")
                return None
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"SERP cache get error for query {query}: {e}")
            return None
    
    async def set_serp_results(
        self,
        query: str,
        country: str,
        language: str,
        serp_results: Union[SearchResponse, Dict[str, Any]],
        page: int = 1,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache SERP results."""
        cache_key = CacheKeyGenerator.serp_results_key(query, country, language, page)
        
        try:
            # Convert to dict if Pydantic model
            if hasattr(serp_results, 'dict'):
                cache_data = serp_results.dict()
            else:
                cache_data = serp_results
            
            # Add cache metadata
            cache_data["_cached_at"] = datetime.utcnow().isoformat()
            cache_data["_cache_key"] = cache_key
            
            success = await self.cache.set(cache_key, cache_data, ttl=ttl, cache_type="serp")
            
            if success:
                self._stats["sets"] += 1
                logger.debug(f"SERP results cached for query: {query}")
                return True
            else:
                self._stats["errors"] += 1
                return False
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"SERP cache set error for query {query}: {e}")
            return False
    
    async def get_crawl_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached crawl content."""
        cache_key = CacheKeyGenerator.crawl_content_key(url)
        
        try:
            result = await self.cache.get(cache_key)
            
            if result:
                self._stats["hits"] += 1
                logger.debug(f"Crawl cache hit for URL: {url}")
                return result
            else:
                self._stats["misses"] += 1
                logger.debug(f"Crawl cache miss for URL: {url}")
                return None
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Crawl cache get error for URL {url}: {e}")
            return None
    
    async def set_crawl_content(
        self,
        url: str,
        crawl_content: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache crawl content."""
        cache_key = CacheKeyGenerator.crawl_content_key(url)
        
        try:
            # Add cache metadata
            cache_data = crawl_content.copy()
            cache_data["_cached_at"] = datetime.utcnow().isoformat()
            cache_data["_cache_key"] = cache_key
            cache_data["_url"] = url
            
            success = await self.cache.set(cache_key, cache_data, ttl=ttl, cache_type="crawl")
            
            if success:
                self._stats["sets"] += 1
                logger.debug(f"Crawl content cached for URL: {url}")
                return True
            else:
                self._stats["errors"] += 1
                return False
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Crawl cache set error for URL {url}: {e}")
            return False
    
    async def invalidate_company(self, company_name: str) -> bool:
        """Invalidate all cache entries for a company."""
        try:
            pattern = f"company:*{company_name.lower()}*"
            deleted_count = await self.cache.clear_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for company: {company_name}")
            return deleted_count > 0
        except Exception as e:
            logger.error(f"Cache invalidation error for company {company_name}: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        redis_stats = await self.cache.get_stats()
        
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "redis": redis_stats,
            "service_stats": {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "errors": self._stats["errors"],
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests
            }
        }
    
    async def warm_cache(self) -> Dict[str, Any]:
        """Warm cache with popular companies and search patterns."""
        try:
            # Warm popular companies
            company_results = await self.cache_warmer.warm_popular_companies()
            
            # Warm common search patterns
            search_patterns = [
                "OpenAI company information",
                "Google contact information", 
                "Microsoft about us",
                "startup funding investors",
                "tech company crunchbase"
            ]
            search_results = await self.cache_warmer.warm_search_patterns(search_patterns)
            
            return {
                "status": "completed",
                "companies": company_results,
                "search_patterns": search_results,
                "total_companies": len(company_results),
                "total_search_patterns": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global cache service instance
_cache_service: Optional[CompanyCacheService] = None


async def get_cache_service() -> CompanyCacheService:
    """Get or create global cache service instance."""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CompanyCacheService()
        await _cache_service.cache.connect()
    
    return _cache_service


async def cleanup_cache_service():
    """Cleanup global cache service."""
    global _cache_service
    
    if _cache_service:
        await _cache_service.cache.disconnect()
        _cache_service = None