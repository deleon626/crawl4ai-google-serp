"""Concurrent processing service for optimized company extraction with rate limiting."""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque

from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, 
    CompanyInformation, ExtractionMetadata, ExtractionError
)
from app.services.company_service import CompanyExtractionService
from app.utils.caching import get_cache_service, CompanyCacheService

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyConfig:
    """Configuration for concurrent processing."""
    max_concurrent_extractions: int = 5
    max_concurrent_searches: int = 10
    max_concurrent_crawls: int = 8
    search_rate_limit: float = 0.5  # Seconds between searches
    crawl_rate_limit: float = 1.0   # Seconds between crawls
    extraction_rate_limit: float = 2.0  # Seconds between extractions
    request_timeout: int = 30
    batch_size: int = 10
    enable_cache_optimization: bool = True


@dataclass
class ProcessingTask:
    """Individual processing task."""
    task_id: str
    request: CompanyInformationRequest
    priority: float = 1.0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, max_tokens: int, refill_rate: float, refill_interval: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            max_tokens: Maximum number of tokens in bucket
            refill_rate: Tokens to add per refill interval
            refill_interval: How often to refill tokens (seconds)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        
        logger.debug(f"RateLimiter initialized: {max_tokens} tokens, {refill_rate}/s rate")
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if not enough available
        """
        async with self._lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Acquired {tokens} tokens, {self.tokens} remaining")
                return True
            else:
                logger.debug(f"Rate limit: insufficient tokens ({self.tokens} < {tokens})")
                return False
    
    async def wait_for_tokens(self, tokens: int = 1, max_wait: float = 30.0) -> bool:
        """
        Wait for tokens to become available.
        
        Args:
            tokens: Number of tokens needed
            max_wait: Maximum time to wait (seconds)
            
        Returns:
            True if tokens acquired, False if timeout
        """
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait:
            if await self.acquire(tokens):
                return True
            
            # Calculate wait time for next refill
            async with self._lock:
                next_refill = self.last_refill + self.refill_interval
                wait_time = max(0.1, next_refill - time.time())
            
            await asyncio.sleep(min(wait_time, 1.0))
        
        logger.warning(f"Rate limiter timeout waiting for {tokens} tokens")
        return False
    
    async def _refill(self):
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed >= self.refill_interval:
            tokens_to_add = int(elapsed / self.refill_interval) * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if tokens_to_add > 0:
                logger.debug(f"Refilled {tokens_to_add} tokens, total: {self.tokens}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        return {
            "tokens_available": self.tokens,
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "utilization": (self.max_tokens - self.tokens) / self.max_tokens * 100
        }


class TaskQueue:
    """Priority-based task queue with concurrency control."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize task queue."""
        self.max_size = max_size
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._processing: Set[str] = set()
        self._completed: Dict[str, Any] = {}
        self._failed: Dict[str, Any] = {}
        self._stats = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total_processing_time": 0.0
        }
        self._lock = asyncio.Lock()
        
        logger.info(f"TaskQueue initialized with max_size: {max_size}")
    
    async def enqueue(self, task: ProcessingTask) -> bool:
        """Add task to queue."""
        try:
            # Priority queue uses negative priority for max-heap behavior
            await self._queue.put((-task.priority, task.created_at, task))
            
            async with self._lock:
                self._stats["queued"] += 1
            
            logger.debug(f"Task queued: {task.task_id} (priority: {task.priority})")
            return True
            
        except asyncio.QueueFull:
            logger.error(f"Task queue full, cannot enqueue: {task.task_id}")
            return False
        except Exception as e:
            logger.error(f"Error enqueueing task {task.task_id}: {e}")
            return False
    
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[ProcessingTask]:
        """Get next task from queue."""
        try:
            _, _, task = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            
            async with self._lock:
                self._processing.add(task.task_id)
                self._stats["processing"] += 1
                self._stats["queued"] -= 1
            
            task.started_at = datetime.utcnow()
            logger.debug(f"Task dequeued: {task.task_id}")
            return task
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error dequeuing task: {e}")
            return None
    
    async def complete_task(self, task_id: str, result: Any, processing_time: float):
        """Mark task as completed."""
        async with self._lock:
            if task_id in self._processing:
                self._processing.remove(task_id)
                self._completed[task_id] = {
                    "result": result,
                    "completed_at": datetime.utcnow(),
                    "processing_time": processing_time
                }
                self._stats["processing"] -= 1
                self._stats["completed"] += 1
                self._stats["total_processing_time"] += processing_time
                
                logger.debug(f"Task completed: {task_id} ({processing_time:.2f}s)")
    
    async def fail_task(self, task_id: str, error: Exception, processing_time: float):
        """Mark task as failed."""
        async with self._lock:
            if task_id in self._processing:
                self._processing.remove(task_id)
                self._failed[task_id] = {
                    "error": str(error),
                    "failed_at": datetime.utcnow(),
                    "processing_time": processing_time
                }
                self._stats["processing"] -= 1
                self._stats["failed"] += 1
                
                logger.debug(f"Task failed: {task_id} - {error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        total_tasks = (self._stats["completed"] + self._stats["failed"])
        avg_processing_time = (
            self._stats["total_processing_time"] / total_tasks
            if total_tasks > 0 else 0.0
        )
        
        return {
            "queued": self._stats["queued"],
            "processing": self._stats["processing"],
            "completed": self._stats["completed"],
            "failed": self._stats["failed"],
            "total_tasks": total_tasks,
            "avg_processing_time": avg_processing_time,
            "queue_size": self._queue.qsize()
        }
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty() and len(self._processing) == 0


class ConcurrentExtractionService:
    """High-performance concurrent company extraction service."""
    
    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        """Initialize concurrent extraction service."""
        self.config = config or ConcurrencyConfig()
        
        # Task management
        self.task_queue = TaskQueue()
        
        # Rate limiters for different operations
        self.search_limiter = RateLimiter(
            max_tokens=self.config.max_concurrent_searches,
            refill_rate=1.0 / self.config.search_rate_limit
        )
        
        self.crawl_limiter = RateLimiter(
            max_tokens=self.config.max_concurrent_crawls,
            refill_rate=1.0 / self.config.crawl_rate_limit
        )
        
        self.extraction_limiter = RateLimiter(
            max_tokens=self.config.max_concurrent_extractions,
            refill_rate=1.0 / self.config.extraction_rate_limit
        )
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Services
        self._extraction_service: Optional[CompanyExtractionService] = None
        self._cache_service: Optional[CompanyCacheService] = None
        
        # Performance tracking
        self._performance_metrics = defaultdict(list)
        
        logger.info(f"ConcurrentExtractionService initialized with config: {self.config}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the concurrent processing service."""
        logger.info("Starting concurrent extraction service")
        
        # Initialize services
        self._extraction_service = CompanyExtractionService()
        await self._extraction_service.__aenter__()
        
        if self.config.enable_cache_optimization:
            self._cache_service = await get_cache_service()
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_extractions):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Started {len(self._workers)} concurrent workers")
    
    async def stop(self):
        """Stop the concurrent processing service."""
        logger.info("Stopping concurrent extraction service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for workers to complete
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
        
        # Cleanup services
        if self._extraction_service:
            await self._extraction_service.__aexit__(None, None, None)
            self._extraction_service = None
        
        logger.info("Concurrent extraction service stopped")
    
    async def extract_company_async(
        self, 
        request: CompanyInformationRequest,
        priority: float = 1.0
    ) -> str:
        """
        Submit company extraction request for async processing.
        
        Args:
            request: Company extraction request
            priority: Processing priority (higher = more urgent)
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())[:12]
        
        # Check cache first if enabled
        if self._cache_service and self.config.enable_cache_optimization:
            cached_result = await self._cache_service.get_company_info(
                request.company_name,
                request.domain,
                request.extraction_mode.value
            )
            
            if cached_result:
                logger.info(f"Cache hit for company: {request.company_name}")
                # Convert cached result to response format
                cached_response = self._create_cached_response(task_id, request, cached_result)
                await self.task_queue.complete_task(task_id, cached_response, 0.0)
                return task_id
        
        # Create processing task
        task = ProcessingTask(
            task_id=task_id,
            request=request,
            priority=priority
        )
        
        # Enqueue for processing
        success = await self.task_queue.enqueue(task)
        
        if success:
            logger.info(f"Queued extraction task: {task_id} for company: {request.company_name}")
            return task_id
        else:
            logger.error(f"Failed to queue task for company: {request.company_name}")
            raise Exception("Task queue full, please try again later")
    
    async def extract_companies_batch(
        self, 
        requests: List[CompanyInformationRequest],
        priority: float = 1.0
    ) -> List[str]:
        """
        Submit batch of company extraction requests.
        
        Args:
            requests: List of company extraction requests
            priority: Processing priority for all requests
            
        Returns:
            List of task IDs for tracking
        """
        task_ids = []
        
        logger.info(f"Processing batch of {len(requests)} company extraction requests")
        
        for request in requests:
            try:
                task_id = await self.extract_company_async(request, priority)
                task_ids.append(task_id)
                
                # Small delay to avoid overwhelming the queue
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Failed to queue batch request for {request.company_name}: {e}")
                # Continue with other requests
        
        logger.info(f"Queued {len(task_ids)}/{len(requests)} batch requests")
        return task_ids
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task."""
        # Check if completed
        if task_id in self.task_queue._completed:
            result_info = self.task_queue._completed[task_id]
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result_info["result"],
                "completed_at": result_info["completed_at"].isoformat(),
                "processing_time": result_info["processing_time"]
            }
        
        # Check if failed
        if task_id in self.task_queue._failed:
            error_info = self.task_queue._failed[task_id]
            return {
                "task_id": task_id,
                "status": "failed",
                "error": error_info["error"],
                "failed_at": error_info["failed_at"].isoformat()
            }
        
        # Check if processing
        if task_id in self.task_queue._processing:
            return {
                "task_id": task_id,
                "status": "processing"
            }
        
        # Must be queued
        return {
            "task_id": task_id,
            "status": "queued"
        }
    
    async def wait_for_completion(
        self, 
        task_ids: List[str], 
        timeout: Optional[float] = None
    ) -> Dict[str, CompanyExtractionResponse]:
        """
        Wait for multiple tasks to complete.
        
        Args:
            task_ids: List of task IDs to wait for
            timeout: Maximum time to wait (seconds)
            
        Returns:
            Dictionary of task_id -> result mappings
        """
        results = {}
        start_time = time.time()
        
        logger.info(f"Waiting for {len(task_ids)} tasks to complete")
        
        while task_ids:
            completed_tasks = []
            
            for task_id in task_ids:
                status = await self.get_task_status(task_id)
                
                if status["status"] == "completed":
                    results[task_id] = status["result"]
                    completed_tasks.append(task_id)
                elif status["status"] == "failed":
                    logger.error(f"Task {task_id} failed: {status['error']}")
                    completed_tasks.append(task_id)
            
            # Remove completed tasks
            for task_id in completed_tasks:
                task_ids.remove(task_id)
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for {len(task_ids)} tasks")
                break
            
            if task_ids:  # Still have pending tasks
                await asyncio.sleep(0.5)
        
        logger.info(f"Completed waiting: {len(results)} results collected")
        return results
    
    async def _worker(self, worker_id: str):
        """Worker task that processes extraction requests."""
        logger.info(f"Worker {worker_id} started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get next task from queue
                task = await self.task_queue.dequeue(timeout=1.0)
                
                if task is None:
                    continue  # Timeout, check shutdown and try again
                
                logger.debug(f"Worker {worker_id} processing task: {task.task_id}")
                
                # Wait for extraction rate limit
                if not await self.extraction_limiter.wait_for_tokens(1, max_wait=10.0):
                    await self.task_queue.fail_task(
                        task.task_id,
                        Exception("Rate limit timeout"),
                        0.0
                    )
                    continue
                
                # Process the task
                start_time = time.time()
                
                try:
                    # Perform extraction
                    result = await self._extraction_service.extract_company_information(task.request)
                    processing_time = time.time() - start_time
                    
                    # Cache result if successful and caching enabled
                    if (result.success and 
                        result.company_information and 
                        self._cache_service and 
                        self.config.enable_cache_optimization):
                        
                        await self._cache_service.set_company_info(
                            task.request.company_name,
                            result.company_information,
                            task.request.domain,
                            task.request.extraction_mode.value
                        )
                    
                    # Record metrics
                    self._record_metrics(worker_id, task, processing_time, True)
                    
                    # Complete task
                    await self.task_queue.complete_task(task.task_id, result, processing_time)
                    
                    logger.debug(f"Worker {worker_id} completed task: {task.task_id} "
                               f"({processing_time:.2f}s)")
                
                except Exception as e:
                    processing_time = time.time() - start_time
                    logger.error(f"Worker {worker_id} error processing task {task.task_id}: {e}")
                    
                    # Record metrics
                    self._record_metrics(worker_id, task, processing_time, False)
                    
                    # Fail task
                    await self.task_queue.fail_task(task.task_id, e, processing_time)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retrying
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _record_metrics(self, worker_id: str, task: ProcessingTask, processing_time: float, success: bool):
        """Record performance metrics."""
        metrics = {
            "worker_id": worker_id,
            "task_id": task.task_id,
            "company_name": task.request.company_name,
            "processing_time": processing_time,
            "success": success,
            "timestamp": datetime.utcnow(),
            "queue_wait_time": (task.started_at - task.created_at).total_seconds() if task.started_at else 0
        }
        
        self._performance_metrics[datetime.utcnow().strftime("%Y-%m-%d_%H")].append(metrics)
        
        # Keep only last 24 hours of metrics
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        cutoff_key = cutoff_time.strftime("%Y-%m-%d_%H")
        
        keys_to_remove = [k for k in self._performance_metrics.keys() if k < cutoff_key]
        for key in keys_to_remove:
            del self._performance_metrics[key]
    
    def _create_cached_response(
        self, 
        task_id: str, 
        request: CompanyInformationRequest, 
        cached_data: Dict[str, Any]
    ) -> CompanyExtractionResponse:
        """Create response from cached data."""
        try:
            # Convert cached data back to CompanyInformation
            company_info = CompanyInformation(**cached_data)
            
            # Create metadata indicating cache hit
            metadata = ExtractionMetadata(
                pages_crawled=0,
                pages_attempted=0,
                extraction_time=0.0,
                sources_found=["cache"],
                search_queries_used=[],
                extraction_mode_used=request.extraction_mode
            )
            
            return CompanyExtractionResponse(
                request_id=task_id,
                company_name=request.company_name,
                success=True,
                company_information=company_info,
                extraction_metadata=metadata,
                errors=[],
                warnings=["Result served from cache"],
                processing_time=0.0
            )
            
        except Exception as e:
            logger.error(f"Error creating cached response: {e}")
            # Return error response
            return CompanyExtractionResponse(
                request_id=task_id,
                company_name=request.company_name,
                success=False,
                company_information=None,
                extraction_metadata=ExtractionMetadata(
                    pages_crawled=0,
                    pages_attempted=0,
                    extraction_time=0.0,
                    sources_found=[],
                    search_queries_used=[],
                    extraction_mode_used=request.extraction_mode
                ),
                errors=[ExtractionError(
                    error_type="CacheError",
                    error_message=f"Failed to process cached data: {str(e)}"
                )],
                warnings=[],
                processing_time=0.0
            )
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        queue_stats = self.task_queue.get_stats()
        
        # Calculate recent performance
        recent_metrics = []
        cutoff_time = datetime.utcnow() - timedelta(hours=1)  # Last hour
        
        for hour_metrics in self._performance_metrics.values():
            for metric in hour_metrics:
                if metric["timestamp"] > cutoff_time:
                    recent_metrics.append(metric)
        
        # Calculate aggregates
        if recent_metrics:
            total_tasks = len(recent_metrics)
            successful_tasks = sum(1 for m in recent_metrics if m["success"])
            avg_processing_time = sum(m["processing_time"] for m in recent_metrics) / total_tasks
            avg_queue_wait = sum(m["queue_wait_time"] for m in recent_metrics) / total_tasks
            success_rate = successful_tasks / total_tasks * 100
        else:
            total_tasks = successful_tasks = 0
            avg_processing_time = avg_queue_wait = success_rate = 0.0
        
        return {
            "queue_stats": queue_stats,
            "rate_limiters": {
                "search": self.search_limiter.get_status(),
                "crawl": self.crawl_limiter.get_status(),
                "extraction": self.extraction_limiter.get_status()
            },
            "recent_performance": {
                "total_tasks_last_hour": total_tasks,
                "successful_tasks_last_hour": successful_tasks,
                "success_rate_percent": round(success_rate, 2),
                "avg_processing_time_seconds": round(avg_processing_time, 2),
                "avg_queue_wait_seconds": round(avg_queue_wait, 2)
            },
            "workers": {
                "active_workers": len(self._workers),
                "max_workers": self.config.max_concurrent_extractions
            },
            "configuration": {
                "max_concurrent_extractions": self.config.max_concurrent_extractions,
                "max_concurrent_searches": self.config.max_concurrent_searches,
                "max_concurrent_crawls": self.config.max_concurrent_crawls,
                "cache_optimization_enabled": self.config.enable_cache_optimization
            }
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            queue_stats = self.task_queue.get_stats()
            
            # Check if workers are responsive
            workers_healthy = len(self._workers) == self.config.max_concurrent_extractions
            
            # Check rate limiter health
            search_limiter_health = self.search_limiter.tokens > 0
            crawl_limiter_health = self.crawl_limiter.tokens > 0
            extraction_limiter_health = self.extraction_limiter.tokens > 0
            
            # Overall health determination
            overall_health = (
                workers_healthy and
                search_limiter_health and
                crawl_limiter_health and
                extraction_limiter_health and
                not self._shutdown_event.is_set()
            )
            
            return {
                "status": "healthy" if overall_health else "degraded",
                "workers_healthy": workers_healthy,
                "active_workers": len(self._workers),
                "queue_size": queue_stats["queued"],
                "processing_tasks": queue_stats["processing"],
                "rate_limiters_healthy": {
                    "search": search_limiter_health,
                    "crawl": crawl_limiter_health,
                    "extraction": extraction_limiter_health
                },
                "cache_service_connected": (
                    self._cache_service.cache.is_connected() 
                    if self._cache_service else False
                ),
                "shutdown_requested": self._shutdown_event.is_set()
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }