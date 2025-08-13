"""
Comprehensive rate limiting and abuse prevention system.

This module provides multi-tier rate limiting, intelligent abuse detection,
and distributed rate limiting capabilities for production environments.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from ipaddress import ip_address, ip_network

import aioredis
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Types of rate limits."""
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


class ThreatLevel(str, Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitRule(BaseModel):
    """Rate limiting rule configuration."""
    
    name: str = Field(description="Rule name")
    limit_type: RateLimitType = Field(description="Type of rate limit")
    requests_per_window: int = Field(description="Number of requests allowed per window")
    window_seconds: int = Field(description="Time window in seconds")
    endpoints: Optional[List[str]] = Field(default=None, description="Specific endpoints (if applicable)")
    user_agents: Optional[List[str]] = Field(default=None, description="Specific user agents (if applicable)")
    ip_whitelist: Optional[List[str]] = Field(default=None, description="IP addresses exempt from this rule")
    priority: int = Field(default=100, description="Rule priority (lower = higher priority)")
    enabled: bool = Field(default=True, description="Whether rule is active")


class SecurityEvent(BaseModel):
    """Security event for audit logging."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str = Field(description="Type of security event")
    client_ip: str = Field(description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    endpoint: str = Field(description="API endpoint accessed")
    threat_level: ThreatLevel = Field(description="Assessed threat level")
    details: Dict = Field(default_factory=dict, description="Additional event details")
    action_taken: str = Field(description="Action taken in response")


class RequestPattern(BaseModel):
    """Request pattern analysis for abuse detection."""
    
    client_id: str = Field(description="Client identifier (IP or user)")
    request_count: int = Field(default=0, description="Total requests")
    unique_endpoints: Set[str] = Field(default_factory=set, description="Unique endpoints accessed")
    user_agents: Set[str] = Field(default_factory=set, description="User agents used")
    request_intervals: List[float] = Field(default_factory=list, description="Time intervals between requests")
    error_rate: float = Field(default=0.0, description="Error rate percentage")
    suspicious_score: float = Field(default=0.0, description="Calculated suspicion score")
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class InMemoryRateLimiter:
    """In-memory rate limiter for single instance deployments."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_clients: Dict[str, datetime] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove old request records to prevent memory leaks."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = now - 3600  # Keep 1 hour of history
        for client_id in list(self.requests.keys()):
            queue = self.requests[client_id]
            while queue and queue[0] < cutoff_time:
                queue.popleft()
            
            if not queue:
                del self.requests[client_id]
        
        # Clean up expired blocks
        expired_blocks = [
            client_id for client_id, block_until in self.blocked_clients.items()
            if datetime.utcnow() > block_until
        ]
        for client_id in expired_blocks:
            del self.blocked_clients[client_id]
        
        self.last_cleanup = now
    
    def is_allowed(self, client_id: str, rule: RateLimitRule) -> Tuple[bool, Dict]:
        """Check if request is allowed under rate limit rule."""
        self._cleanup_old_requests()
        
        # Check if client is blocked
        if client_id in self.blocked_clients:
            block_until = self.blocked_clients[client_id]
            if datetime.utcnow() < block_until:
                return False, {
                    "reason": "client_blocked",
                    "blocked_until": block_until.isoformat(),
                    "remaining_time": (block_until - datetime.utcnow()).total_seconds()
                }
            else:
                del self.blocked_clients[client_id]
        
        # Get request history
        now = time.time()
        window_start = now - rule.window_seconds
        queue = self.requests[client_id]
        
        # Remove old requests outside window
        while queue and queue[0] < window_start:
            queue.popleft()
        
        # Check if limit exceeded
        current_count = len(queue)
        if current_count >= rule.requests_per_window:
            return False, {
                "reason": "rate_limit_exceeded",
                "rule": rule.name,
                "current_count": current_count,
                "limit": rule.requests_per_window,
                "window_seconds": rule.window_seconds,
                "reset_time": (window_start + rule.window_seconds)
            }
        
        # Record this request
        queue.append(now)
        
        return True, {
            "requests_remaining": rule.requests_per_window - current_count - 1,
            "reset_time": window_start + rule.window_seconds
        }
    
    def block_client(self, client_id: str, duration_seconds: int = 3600):
        """Block client for specified duration."""
        self.blocked_clients[client_id] = datetime.utcnow() + timedelta(seconds=duration_seconds)
        logger.warning(f"Blocked client {client_id} for {duration_seconds} seconds")


class RedisRateLimiter:
    """Redis-based distributed rate limiter."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.key_prefix = "rate_limit:"
        self.block_prefix = "blocked:"
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=settings.redis_retry_on_timeout,
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis for distributed rate limiting")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def is_allowed(self, client_id: str, rule: RateLimitRule) -> Tuple[bool, Dict]:
        """Check if request is allowed using Redis sliding window."""
        if not self.redis:
            raise RuntimeError("Redis connection not available")
        
        # Check if client is blocked
        block_key = f"{self.block_prefix}{client_id}"
        blocked_until = await self.redis.get(block_key)
        if blocked_until:
            block_time = datetime.fromisoformat(blocked_until)
            if datetime.utcnow() < block_time:
                remaining = (block_time - datetime.utcnow()).total_seconds()
                return False, {
                    "reason": "client_blocked",
                    "blocked_until": blocked_until,
                    "remaining_time": remaining
                }
            else:
                await self.redis.delete(block_key)
        
        # Sliding window rate limiting
        key = f"{self.key_prefix}{rule.name}:{client_id}"
        now = time.time()
        window_start = now - rule.window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count >= rule.requests_per_window:
            return False, {
                "reason": "rate_limit_exceeded",
                "rule": rule.name,
                "current_count": current_count,
                "limit": rule.requests_per_window,
                "window_seconds": rule.window_seconds,
                "reset_time": window_start + rule.window_seconds
            }
        
        # Add current request and set expiry
        pipe = self.redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, rule.window_seconds + 1)
        await pipe.execute()
        
        return True, {
            "requests_remaining": rule.requests_per_window - current_count - 1,
            "reset_time": window_start + rule.window_seconds
        }
    
    async def block_client(self, client_id: str, duration_seconds: int = 3600):
        """Block client in Redis."""
        if not self.redis:
            return
        
        block_key = f"{self.block_prefix}{client_id}"
        block_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        await self.redis.setex(
            block_key,
            duration_seconds,
            block_until.isoformat()
        )
        
        logger.warning(f"Blocked client {client_id} for {duration_seconds} seconds")


class AbuseDetector:
    """Intelligent abuse detection system."""
    
    def __init__(self):
        self.client_patterns: Dict[str, RequestPattern] = {}
        self.suspicious_patterns = {
            "rapid_requests": {"threshold": 100, "weight": 0.3},
            "unique_endpoints": {"threshold": 20, "weight": 0.2},
            "user_agent_variety": {"threshold": 5, "weight": 0.15},
            "high_error_rate": {"threshold": 0.5, "weight": 0.25},
            "regular_intervals": {"variance_threshold": 0.1, "weight": 0.1}
        }
        self.max_pattern_age = timedelta(hours=24)
    
    def _calculate_suspicion_score(self, pattern: RequestPattern) -> float:
        """Calculate suspicion score based on request patterns."""
        score = 0.0
        
        # Rapid requests
        requests_per_hour = pattern.request_count / max(
            (pattern.last_seen - pattern.first_seen).total_seconds() / 3600, 0.1
        )
        if requests_per_hour > self.suspicious_patterns["rapid_requests"]["threshold"]:
            score += self.suspicious_patterns["rapid_requests"]["weight"]
        
        # Unique endpoints accessed
        if len(pattern.unique_endpoints) > self.suspicious_patterns["unique_endpoints"]["threshold"]:
            score += self.suspicious_patterns["unique_endpoints"]["weight"]
        
        # User agent variety
        if len(pattern.user_agents) > self.suspicious_patterns["user_agent_variety"]["threshold"]:
            score += self.suspicious_patterns["user_agent_variety"]["weight"]
        
        # High error rate
        if pattern.error_rate > self.suspicious_patterns["high_error_rate"]["threshold"]:
            score += self.suspicious_patterns["high_error_rate"]["weight"]
        
        # Regular intervals (bot-like behavior)
        if len(pattern.request_intervals) > 10:
            intervals = pattern.request_intervals[-10:]  # Last 10 intervals
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            if variance < self.suspicious_patterns["regular_intervals"]["variance_threshold"]:
                score += self.suspicious_patterns["regular_intervals"]["weight"]
        
        return min(score, 1.0)
    
    def record_request(self, client_ip: str, endpoint: str, user_agent: str = None, 
                      is_error: bool = False) -> float:
        """Record request and return updated suspicion score."""
        now = datetime.utcnow()
        
        # Get or create pattern
        if client_ip not in self.client_patterns:
            self.client_patterns[client_ip] = RequestPattern(client_id=client_ip)
        
        pattern = self.client_patterns[client_ip]
        
        # Update pattern
        pattern.request_count += 1
        pattern.unique_endpoints.add(endpoint)
        if user_agent:
            pattern.user_agents.add(user_agent)
        pattern.last_seen = now
        
        # Calculate request interval
        if hasattr(pattern, '_last_request_time'):
            interval = (now - pattern._last_request_time).total_seconds()
            pattern.request_intervals.append(interval)
            # Keep only recent intervals
            if len(pattern.request_intervals) > 100:
                pattern.request_intervals = pattern.request_intervals[-50:]
        
        pattern._last_request_time = now
        
        # Update error rate
        if is_error:
            pattern.error_rate = (pattern.error_rate * (pattern.request_count - 1) + 1) / pattern.request_count
        else:
            pattern.error_rate = (pattern.error_rate * (pattern.request_count - 1)) / pattern.request_count
        
        # Calculate and update suspicion score
        pattern.suspicious_score = self._calculate_suspicion_score(pattern)
        
        return pattern.suspicious_score
    
    def is_suspicious(self, client_ip: str, threshold: float = 0.7) -> Tuple[bool, Dict]:
        """Check if client shows suspicious patterns."""
        pattern = self.client_patterns.get(client_ip)
        if not pattern:
            return False, {}
        
        is_suspicious = pattern.suspicious_score >= threshold
        
        details = {
            "suspicion_score": pattern.suspicious_score,
            "request_count": pattern.request_count,
            "unique_endpoints": len(pattern.unique_endpoints),
            "user_agents": len(pattern.user_agents),
            "error_rate": pattern.error_rate,
            "age_hours": (pattern.last_seen - pattern.first_seen).total_seconds() / 3600
        }
        
        return is_suspicious, details
    
    def cleanup_old_patterns(self):
        """Remove old patterns to prevent memory leaks."""
        cutoff = datetime.utcnow() - self.max_pattern_age
        expired_clients = [
            client_id for client_id, pattern in self.client_patterns.items()
            if pattern.last_seen < cutoff
        ]
        
        for client_id in expired_clients:
            del self.client_patterns[client_id]
        
        if expired_clients:
            logger.info(f"Cleaned up {len(expired_clients)} expired client patterns")


class RateLimitManager:
    """Main rate limiting and abuse prevention manager."""
    
    def __init__(self):
        self.rules: List[RateLimitRule] = []
        self.in_memory_limiter = InMemoryRateLimiter()
        self.redis_limiter: Optional[RedisRateLimiter] = None
        self.abuse_detector = AbuseDetector()
        self.security_events: List[SecurityEvent] = []
        self.max_events_memory = 10000
        
        # Default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        self.rules = [
            # Strict limits for search endpoints (most resource intensive)
            RateLimitRule(
                name="search_endpoint_strict",
                limit_type=RateLimitType.PER_IP,
                requests_per_window=10,
                window_seconds=60,
                endpoints=["/api/v1/search", "/api/v1/search/batch"],
                priority=10
            ),
            
            # Moderate limits for crawl endpoints
            RateLimitRule(
                name="crawl_endpoint_moderate",
                limit_type=RateLimitType.PER_IP,
                requests_per_window=20,
                window_seconds=60,
                endpoints=["/api/v1/crawl"],
                priority=20
            ),
            
            # Generous limits for company endpoints
            RateLimitRule(
                name="company_endpoint_generous",
                limit_type=RateLimitType.PER_IP,
                requests_per_window=50,
                window_seconds=60,
                endpoints=["/api/v1/company/extract", "/api/v1/company/batch_extract"],
                priority=30
            ),
            
            # Global per-IP limit
            RateLimitRule(
                name="global_per_ip",
                limit_type=RateLimitType.PER_IP,
                requests_per_window=100,
                window_seconds=60,
                priority=100
            ),
            
            # Burst protection
            RateLimitRule(
                name="burst_protection",
                limit_type=RateLimitType.PER_IP,
                requests_per_window=200,
                window_seconds=300,  # 5 minutes
                priority=5
            )
        ]
    
    async def initialize(self):
        """Initialize rate limiter with Redis if available."""
        try:
            self.redis_limiter = RedisRateLimiter()
            await self.redis_limiter.connect()
            logger.info("Initialized distributed rate limiting with Redis")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory rate limiting: {e}")
            self.redis_limiter = None
    
    async def shutdown(self):
        """Shutdown rate limiter."""
        if self.redis_limiter:
            await self.redis_limiter.disconnect()
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try to get real IP from headers (behind proxy)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP") or
            request.client.host if request.client else "unknown"
        )
        
        return client_ip
    
    def _is_whitelisted(self, client_ip: str, rule: RateLimitRule) -> bool:
        """Check if client IP is whitelisted for rule."""
        if not rule.ip_whitelist:
            return False
        
        try:
            client = ip_address(client_ip)
            for whitelist_entry in rule.ip_whitelist:
                try:
                    if "/" in whitelist_entry:
                        # CIDR notation
                        if client in ip_network(whitelist_entry, strict=False):
                            return True
                    else:
                        # Single IP
                        if client == ip_address(whitelist_entry):
                            return True
                except ValueError:
                    continue
        except ValueError:
            pass  # Invalid client IP
        
        return False
    
    def _matches_rule(self, request: Request, rule: RateLimitRule) -> bool:
        """Check if request matches rate limit rule criteria."""
        if not rule.enabled:
            return False
        
        client_ip = self._get_client_id(request)
        
        # Check whitelist
        if self._is_whitelisted(client_ip, rule):
            return False
        
        # Check endpoint match
        if rule.endpoints:
            endpoint = str(request.url.path)
            if not any(endpoint.startswith(ep) for ep in rule.endpoints):
                return False
        
        # Check user agent match
        if rule.user_agents:
            user_agent = request.headers.get("user-agent", "")
            if not any(ua.lower() in user_agent.lower() for ua in rule.user_agents):
                return False
        
        return True
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """
        Check if request is allowed under all applicable rate limit rules.
        
        Returns:
            Tuple of (allowed: bool, details: dict)
        """
        client_id = self._get_client_id(request)
        endpoint = str(request.url.path)
        user_agent = request.headers.get("user-agent")
        
        # Record request for abuse detection
        suspicion_score = self.abuse_detector.record_request(
            client_id, endpoint, user_agent
        )
        
        # Check if client is suspicious
        is_suspicious, suspicion_details = self.abuse_detector.is_suspicious(client_id)
        
        # Apply stricter limits for suspicious clients
        applicable_rules = []
        for rule in sorted(self.rules, key=lambda r: r.priority):
            if self._matches_rule(request, rule):
                # Reduce limits for suspicious clients
                if is_suspicious and suspicion_score > 0.8:
                    rule = RateLimitRule(
                        **rule.dict(),
                        requests_per_window=max(1, rule.requests_per_window // 4),
                        name=f"{rule.name}_suspicious"
                    )
                applicable_rules.append(rule)
        
        if not applicable_rules:
            return True, {"message": "No rate limits applied"}
        
        # Check each applicable rule
        limiter = self.redis_limiter if self.redis_limiter else self.in_memory_limiter
        
        for rule in applicable_rules:
            allowed, details = await limiter.is_allowed(client_id, rule)
            
            if not allowed:
                # Log security event
                security_event = SecurityEvent(
                    event_type="rate_limit_exceeded",
                    client_ip=client_id,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    threat_level=ThreatLevel.MEDIUM if not is_suspicious else ThreatLevel.HIGH,
                    details={
                        "rule": rule.name,
                        "suspicion_score": suspicion_score,
                        "suspicion_details": suspicion_details,
                        **details
                    },
                    action_taken="request_blocked"
                )
                
                await self._log_security_event(security_event)
                
                # Block client if highly suspicious
                if is_suspicious and suspicion_score > 0.9:
                    await limiter.block_client(client_id, 3600)  # 1 hour
                    security_event.action_taken = "client_blocked_1h"
                
                return False, {
                    "error": "Rate limit exceeded",
                    "rule": rule.name,
                    "suspicion_score": suspicion_score,
                    **details
                }
        
        return True, {"message": "Request allowed", "suspicion_score": suspicion_score}
    
    async def _log_security_event(self, event: SecurityEvent):
        """Log security event."""
        # Add to in-memory storage
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > self.max_events_memory:
            self.security_events = self.security_events[-self.max_events_memory // 2:]
        
        # Log to application logs
        level = logging.WARNING if event.threat_level in (ThreatLevel.MEDIUM, ThreatLevel.HIGH) else logging.INFO
        logger.log(level, f"Security event: {event.event_type} from {event.client_ip} - {event.action_taken}")
        
        # In production, also send to SIEM/monitoring system
        if self.redis_limiter and self.redis_limiter.redis:
            try:
                event_key = f"security_events:{datetime.utcnow().strftime('%Y%m%d')}"
                await self.redis_limiter.redis.lpush(event_key, event.json())
                await self.redis_limiter.redis.expire(event_key, 604800)  # 7 days
            except Exception as e:
                logger.error(f"Failed to log security event to Redis: {e}")
    
    def add_rule(self, rule: RateLimitRule):
        """Add custom rate limiting rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        logger.info(f"Added rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove rate limiting rule by name."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed rate limiting rule: {rule_name}")
    
    async def get_client_info(self, client_ip: str) -> Dict:
        """Get detailed information about client."""
        pattern = self.abuse_detector.client_patterns.get(client_ip)
        
        info = {
            "client_ip": client_ip,
            "is_blocked": False,
            "pattern_exists": pattern is not None
        }
        
        if pattern:
            info.update({
                "request_count": pattern.request_count,
                "unique_endpoints": len(pattern.unique_endpoints),
                "user_agents_count": len(pattern.user_agents),
                "error_rate": pattern.error_rate,
                "suspicion_score": pattern.suspicious_score,
                "first_seen": pattern.first_seen.isoformat(),
                "last_seen": pattern.last_seen.isoformat()
            })
        
        # Check if blocked
        if self.redis_limiter and self.redis_limiter.redis:
            block_key = f"{self.redis_limiter.block_prefix}{client_ip}"
            blocked_until = await self.redis_limiter.redis.get(block_key)
            if blocked_until:
                info["is_blocked"] = True
                info["blocked_until"] = blocked_until
        else:
            if client_ip in self.in_memory_limiter.blocked_clients:
                info["is_blocked"] = True
                info["blocked_until"] = self.in_memory_limiter.blocked_clients[client_ip].isoformat()
        
        return info
    
    def get_security_events(self, limit: int = 100, threat_level: ThreatLevel = None) -> List[SecurityEvent]:
        """Get recent security events."""
        events = self.security_events
        
        if threat_level:
            events = [e for e in events if e.threat_level == threat_level]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def cleanup(self):
        """Cleanup old data."""
        self.abuse_detector.cleanup_old_patterns()


# Global rate limiter instance
rate_limiter = RateLimitManager()


async def rate_limit_middleware(request: Request):
    """FastAPI middleware for rate limiting."""
    allowed, details = await rate_limiter.check_rate_limit(request)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=details,
            headers={
                "Retry-After": str(int(details.get("remaining_time", 60))),
                "X-RateLimit-Rule": details.get("rule", "unknown")
            }
        )
    
    return details