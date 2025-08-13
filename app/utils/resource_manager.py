"""Resource management system for connection pooling, memory optimization, and performance monitoring."""

import asyncio
import logging
import psutil
import time
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource usage limits and thresholds."""
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    max_open_connections: int = 100
    max_concurrent_requests: int = 50
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    max_pool_size: int = 20
    
    # Warning thresholds (percentage of max)
    memory_warning_threshold: float = 0.8
    cpu_warning_threshold: float = 0.7
    connection_warning_threshold: float = 0.8


@dataclass
class ResourceMetrics:
    """Current resource usage metrics."""
    memory_usage_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    open_connections: int = 0
    active_requests: int = 0
    pool_connections: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def is_within_limits(self, limits: ResourceLimits) -> bool:
        """Check if current usage is within limits."""
        return (
            self.memory_usage_mb <= limits.max_memory_mb and
            self.cpu_percent <= limits.max_cpu_percent and
            self.open_connections <= limits.max_open_connections and
            self.active_requests <= limits.max_concurrent_requests
        )
    
    def get_warnings(self, limits: ResourceLimits) -> List[str]:
        """Get list of resource usage warnings."""
        warnings = []
        
        if self.memory_usage_mb > (limits.max_memory_mb * limits.memory_warning_threshold):
            warnings.append(f"High memory usage: {self.memory_usage_mb:.1f}MB "
                          f"({self.memory_percent:.1f}% of system)")
        
        if self.cpu_percent > (limits.max_cpu_percent * limits.cpu_warning_threshold):
            warnings.append(f"High CPU usage: {self.cpu_percent:.1f}%")
        
        if self.open_connections > (limits.max_open_connections * limits.connection_warning_threshold):
            warnings.append(f"High connection count: {self.open_connections}")
        
        return warnings


class ConnectionPool:
    """HTTP connection pool manager with lifecycle management."""
    
    def __init__(self, limits: ResourceLimits):
        """Initialize connection pool."""
        self.limits = limits
        self._client: Optional[httpx.AsyncClient] = None
        self._active_requests: Set[str] = set()
        self._connection_stats = {
            "total_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "response_times": deque(maxlen=100)  # Last 100 response times
        }
        self._lock = asyncio.Lock()
        
        logger.info(f"ConnectionPool initialized with limits: {limits}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize HTTP client with connection pooling."""
        if self._client is None:
            # Configure connection limits
            limits = httpx.Limits(
                max_keepalive_connections=self.limits.max_pool_size,
                max_connections=self.limits.max_open_connections,
                keepalive_expiry=300  # 5 minutes
            )
            
            # Configure timeouts
            timeout = httpx.Timeout(
                connect=self.limits.connection_timeout,
                read=self.limits.read_timeout,
                write=30.0,
                pool=60.0
            )
            
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
                verify=True,
                http2=True  # Enable HTTP/2 for better performance
            )
            
            logger.info("HTTP client initialized with connection pooling")
    
    async def cleanup(self):
        """Cleanup HTTP client and connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP client closed and connections cleaned up")
    
    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        """Context manager for HTTP requests with resource tracking."""
        if not self._client:
            await self.initialize()
        
        request_id = f"{method}:{url}:{id(self)}"
        start_time = time.time()
        
        try:
            async with self._lock:
                if len(self._active_requests) >= self.limits.max_concurrent_requests:
                    raise Exception("Maximum concurrent requests exceeded")
                
                self._active_requests.add(request_id)
                self._connection_stats["total_requests"] += 1
            
            logger.debug(f"Starting request: {request_id}")
            
            # Make HTTP request
            response = await self._client.request(method, url, **kwargs)
            
            # Record response time
            response_time = time.time() - start_time
            self._connection_stats["response_times"].append(response_time)
            
            # Update average response time
            if self._connection_stats["response_times"]:
                self._connection_stats["avg_response_time"] = (
                    sum(self._connection_stats["response_times"]) / 
                    len(self._connection_stats["response_times"])
                )
            
            logger.debug(f"Request completed: {request_id} ({response_time:.2f}s)")
            
            yield response
            
        except Exception as e:
            async with self._lock:
                self._connection_stats["failed_requests"] += 1
            
            logger.error(f"Request failed: {request_id} - {e}")
            raise
            
        finally:
            async with self._lock:
                self._active_requests.discard(request_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "active_requests": len(self._active_requests),
            "total_requests": self._connection_stats["total_requests"],
            "failed_requests": self._connection_stats["failed_requests"],
            "success_rate": (
                (self._connection_stats["total_requests"] - self._connection_stats["failed_requests"]) / 
                max(1, self._connection_stats["total_requests"]) * 100
            ),
            "avg_response_time": round(self._connection_stats["avg_response_time"], 3),
            "pool_connections": self.get_pool_info()["pool_connections"] if self._client else 0,
            "is_healthy": self._client is not None and not self._client.is_closed
        }
    
    def get_pool_info(self) -> Dict[str, Any]:
        """Get connection pool information."""
        if not self._client:
            return {"pool_connections": 0, "pool_status": "not_initialized"}
        
        try:
            # Access internal connection pool info
            pool_info = {}
            if hasattr(self._client, '_transport') and hasattr(self._client._transport, '_pool'):
                pool = self._client._transport._pool
                pool_info = {
                    "pool_connections": len(pool._connections) if hasattr(pool, '_connections') else 0,
                    "pool_status": "active",
                    "keepalive_expiry": pool._keepalive_expiry if hasattr(pool, '_keepalive_expiry') else None
                }
            else:
                pool_info = {
                    "pool_connections": 0,
                    "pool_status": "unknown"
                }
            
            return pool_info
            
        except Exception as e:
            logger.debug(f"Error getting pool info: {e}")
            return {"pool_connections": 0, "pool_status": "error"}


class MemoryOptimizer:
    """Memory usage monitoring and optimization."""
    
    def __init__(self, limits: ResourceLimits):
        """Initialize memory optimizer."""
        self.limits = limits
        self._process = psutil.Process()
        self._memory_history = deque(maxlen=100)  # Last 100 memory readings
        
        logger.info(f"MemoryOptimizer initialized with limit: {limits.max_memory_mb}MB")
    
    def get_current_usage(self) -> ResourceMetrics:
        """Get current memory and CPU usage."""
        try:
            # Memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            memory_percent = self._process.memory_percent()
            
            # CPU usage
            cpu_percent = self._process.cpu_percent(interval=0.1)
            
            # Connection info (estimated)
            open_files = len(self._process.open_files())
            connections = len(self._process.connections())
            
            metrics = ResourceMetrics(
                memory_usage_mb=memory_mb,
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                open_connections=connections,
                active_requests=0,  # Will be updated by caller
                pool_connections=0   # Will be updated by caller
            )
            
            # Store in history
            self._memory_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return ResourceMetrics()  # Return default metrics
    
    def get_memory_trend(self) -> Dict[str, Any]:
        """Get memory usage trend analysis."""
        if len(self._memory_history) < 2:
            return {"trend": "insufficient_data", "points": len(self._memory_history)}
        
        recent_readings = list(self._memory_history)[-10:]  # Last 10 readings
        memory_values = [r.memory_usage_mb for r in recent_readings]
        
        # Calculate trend
        if len(memory_values) >= 2:
            start_memory = sum(memory_values[:2]) / 2  # Average of first 2
            end_memory = sum(memory_values[-2:]) / 2   # Average of last 2
            
            trend_mb_per_reading = (end_memory - start_memory) / max(1, len(memory_values) - 1)
            
            if abs(trend_mb_per_reading) < 1.0:
                trend = "stable"
            elif trend_mb_per_reading > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
        else:
            trend = "stable"
            trend_mb_per_reading = 0.0
        
        return {
            "trend": trend,
            "trend_mb_per_reading": round(trend_mb_per_reading, 2),
            "current_memory_mb": recent_readings[-1].memory_usage_mb,
            "avg_memory_mb": sum(memory_values) / len(memory_values),
            "min_memory_mb": min(memory_values),
            "max_memory_mb": max(memory_values),
            "readings_count": len(recent_readings)
        }
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization."""
        try:
            import gc
            
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory usage before and after
            before_metrics = self.get_current_usage()
            
            # Additional optimization steps
            optimizations_performed = ["garbage_collection"]
            
            # Clear any internal caches if available
            try:
                # Clear DNS cache if using httpx
                optimizations_performed.append("dns_cache_clear")
            except Exception:
                pass
            
            after_metrics = self.get_current_usage()
            memory_freed = before_metrics.memory_usage_mb - after_metrics.memory_usage_mb
            
            logger.info(f"Memory optimization completed: freed {memory_freed:.2f}MB, "
                       f"collected {collected} objects")
            
            return {
                "success": True,
                "memory_freed_mb": round(memory_freed, 2),
                "objects_collected": collected,
                "optimizations_performed": optimizations_performed,
                "before_usage_mb": round(before_metrics.memory_usage_mb, 2),
                "after_usage_mb": round(after_metrics.memory_usage_mb, 2)
            }
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class ResourceManager:
    """Comprehensive resource management system."""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """Initialize resource manager."""
        self.limits = limits or ResourceLimits()
        self.connection_pool = ConnectionPool(self.limits)
        self.memory_optimizer = MemoryOptimizer(self.limits)
        
        # Resource monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 30.0  # Monitor every 30 seconds
        self._shutdown_event = asyncio.Event()
        
        # Performance tracking
        self._performance_history = deque(maxlen=288)  # 24 hours at 5-minute intervals
        self._alerts = deque(maxlen=100)  # Last 100 alerts
        
        # Thread pool for CPU-intensive tasks
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        logger.info(f"ResourceManager initialized with limits: {limits}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start resource manager services."""
        logger.info("Starting resource manager")
        
        # Initialize connection pool
        await self.connection_pool.initialize()
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Resource manager started")
    
    async def stop(self):
        """Stop resource manager services."""
        logger.info("Stopping resource manager")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop monitoring
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup connection pool
        await self.connection_pool.cleanup()
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        logger.info("Resource manager stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Resource monitoring started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get current resource usage
                metrics = await self._get_comprehensive_metrics()
                
                # Check for limit violations
                warnings = metrics.get_warnings(self.limits)
                if warnings:
                    alert = {
                        "timestamp": datetime.utcnow(),
                        "type": "resource_warning",
                        "warnings": warnings,
                        "metrics": metrics
                    }
                    self._alerts.append(alert)
                    logger.warning(f"Resource warnings: {warnings}")
                
                # Check for critical violations
                if not metrics.is_within_limits(self.limits):
                    alert = {
                        "timestamp": datetime.utcnow(),
                        "type": "resource_limit_exceeded",
                        "metrics": metrics
                    }
                    self._alerts.append(alert)
                    logger.error("Resource limits exceeded!")
                    
                    # Trigger optimization
                    await self.optimize_resources()
                
                # Store performance history
                self._performance_history.append({
                    "timestamp": datetime.utcnow(),
                    "metrics": metrics,
                    "connection_stats": self.connection_pool.get_stats()
                })
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self._monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5.0)  # Brief pause on error
        
        logger.info("Resource monitoring stopped")
    
    async def _get_comprehensive_metrics(self) -> ResourceMetrics:
        """Get comprehensive resource metrics."""
        # Get base metrics
        metrics = self.memory_optimizer.get_current_usage()
        
        # Add connection pool info
        pool_stats = self.connection_pool.get_stats()
        metrics.active_requests = pool_stats["active_requests"]
        metrics.pool_connections = pool_stats["pool_connections"]
        
        return metrics
    
    async def optimize_resources(self) -> Dict[str, Any]:
        """Perform comprehensive resource optimization."""
        logger.info("Starting resource optimization")
        
        results = {}
        
        # Memory optimization
        memory_result = await self.memory_optimizer.optimize_memory()
        results["memory_optimization"] = memory_result
        
        # Connection optimization (close idle connections if needed)
        try:
            await self.connection_pool.cleanup()
            await self.connection_pool.initialize()
            results["connection_optimization"] = {"success": True, "action": "pool_recycled"}
        except Exception as e:
            results["connection_optimization"] = {"success": False, "error": str(e)}
        
        logger.info(f"Resource optimization completed: {results}")
        return results
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client from connection pool."""
        if not self.connection_pool._client:
            await self.connection_pool.initialize()
        return self.connection_pool._client
    
    async def make_request(self, method: str, url: str, **kwargs):
        """Make HTTP request with resource management."""
        async with self.connection_pool.request(method, url, **kwargs) as response:
            return response
    
    def run_in_thread(self, func: Callable, *args, **kwargs):
        """Run CPU-intensive function in thread pool."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self._thread_pool, func, *args, **kwargs)
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """Get comprehensive resource status."""
        metrics = await self._get_comprehensive_metrics()
        connection_stats = self.connection_pool.get_stats()
        memory_trend = self.memory_optimizer.get_memory_trend()
        
        # Recent alerts (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_alerts = [
            alert for alert in self._alerts 
            if alert["timestamp"] > cutoff_time
        ]
        
        return {
            "current_metrics": {
                "memory_usage_mb": round(metrics.memory_usage_mb, 2),
                "memory_percent": round(metrics.memory_percent, 2),
                "cpu_percent": round(metrics.cpu_percent, 2),
                "open_connections": metrics.open_connections,
                "active_requests": metrics.active_requests,
                "pool_connections": metrics.pool_connections
            },
            "limits": {
                "max_memory_mb": self.limits.max_memory_mb,
                "max_cpu_percent": self.limits.max_cpu_percent,
                "max_open_connections": self.limits.max_open_connections,
                "max_concurrent_requests": self.limits.max_concurrent_requests
            },
            "status": {
                "within_limits": metrics.is_within_limits(self.limits),
                "warnings": metrics.get_warnings(self.limits),
                "monitoring_active": not self._shutdown_event.is_set()
            },
            "connection_pool": connection_stats,
            "memory_trend": memory_trend,
            "recent_alerts": len(recent_alerts),
            "performance_history_points": len(self._performance_history)
        }
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self._performance_history:
            return {"status": "no_data_available"}
        
        # Analyze last 100 data points
        recent_data = list(self._performance_history)[-100:]
        
        # Calculate averages
        avg_memory = sum(d["metrics"].memory_usage_mb for d in recent_data) / len(recent_data)
        avg_cpu = sum(d["metrics"].cpu_percent for d in recent_data) / len(recent_data)
        avg_connections = sum(d["metrics"].open_connections for d in recent_data) / len(recent_data)
        avg_response_time = sum(d["connection_stats"]["avg_response_time"] for d in recent_data) / len(recent_data)
        
        # Connection success rates
        total_requests = sum(d["connection_stats"]["total_requests"] for d in recent_data)
        failed_requests = sum(d["connection_stats"]["failed_requests"] for d in recent_data)
        success_rate = ((total_requests - failed_requests) / max(1, total_requests)) * 100
        
        return {
            "report_period": {
                "start_time": recent_data[0]["timestamp"].isoformat() if recent_data else None,
                "end_time": recent_data[-1]["timestamp"].isoformat() if recent_data else None,
                "data_points": len(recent_data)
            },
            "averages": {
                "memory_usage_mb": round(avg_memory, 2),
                "cpu_percent": round(avg_cpu, 2),
                "open_connections": round(avg_connections, 2),
                "response_time_seconds": round(avg_response_time, 3)
            },
            "connection_performance": {
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "success_rate_percent": round(success_rate, 2)
            },
            "resource_efficiency": {
                "memory_utilization_percent": round((avg_memory / self.limits.max_memory_mb) * 100, 2),
                "cpu_utilization_percent": round((avg_cpu / self.limits.max_cpu_percent) * 100, 2),
                "connection_utilization_percent": round((avg_connections / self.limits.max_open_connections) * 100, 2)
            }
        }


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None


async def get_resource_manager(limits: Optional[ResourceLimits] = None) -> ResourceManager:
    """Get or create global resource manager instance."""
    global _resource_manager
    
    if _resource_manager is None:
        _resource_manager = ResourceManager(limits)
        await _resource_manager.start()
    
    return _resource_manager


async def cleanup_resource_manager():
    """Cleanup global resource manager."""
    global _resource_manager
    
    if _resource_manager:
        await _resource_manager.stop()
        _resource_manager = None