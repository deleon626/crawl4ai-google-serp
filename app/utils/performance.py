"""Performance monitoring system with real-time metrics, bottleneck detection, and optimization feedback."""

import asyncio
import logging
import time
import statistics
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceLevel(str, Enum):
    """Performance level classifications."""
    EXCELLENT = "excellent"      # < 1s response time, < 50% resource usage
    GOOD = "good"               # < 3s response time, < 70% resource usage
    ACCEPTABLE = "acceptable"   # < 10s response time, < 85% resource usage
    POOR = "poor"              # < 30s response time, < 95% resource usage
    CRITICAL = "critical"       # > 30s response time or > 95% resource usage


class BottleneckType(str, Enum):
    """Types of performance bottlenecks."""
    CPU_BOUND = "cpu_bound"           # High CPU usage
    MEMORY_BOUND = "memory_bound"     # High memory usage
    IO_BOUND = "io_bound"            # Network/disk I/O delays
    RATE_LIMITED = "rate_limited"     # API rate limiting
    CONCURRENCY_LIMITED = "concurrency_limited"  # Queue saturation
    RESOURCE_CONTENTION = "resource_contention"   # Resource conflicts


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def is_within_threshold(self, threshold: float, comparison: str = "less") -> bool:
        """Check if metric is within threshold."""
        if comparison == "less":
            return self.value < threshold
        elif comparison == "greater":
            return self.value > threshold
        elif comparison == "equal":
            return abs(self.value - threshold) < 0.001
        else:
            return False


@dataclass
class PerformanceAlert:
    """Performance alert/recommendation."""
    alert_type: str
    severity: str
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BottleneckAnalysis:
    """Bottleneck detection analysis."""
    bottleneck_type: BottleneckType
    severity: float  # 0.0 - 1.0
    affected_operations: List[str]
    root_cause: str
    impact_description: str
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Real-time performance metrics collection."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector."""
        self.max_history = max_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._aggregates: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        
        logger.info(f"MetricsCollector initialized with max_history: {max_history}")
    
    async def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        async with self._lock:
            self._metrics[metric.name].append(metric)
            await self._update_aggregates(metric.name)
    
    async def record_metrics(self, metrics: List[PerformanceMetric]):
        """Record multiple metrics efficiently."""
        async with self._lock:
            updated_names = set()
            
            for metric in metrics:
                self._metrics[metric.name].append(metric)
                updated_names.add(metric.name)
            
            # Update aggregates for all affected metrics
            for name in updated_names:
                await self._update_aggregates(name)
    
    async def _update_aggregates(self, metric_name: str):
        """Update aggregate statistics for a metric."""
        metric_history = self._metrics[metric_name]
        
        if not metric_history:
            return
        
        values = [m.value for m in metric_history]
        
        self._aggregates[metric_name] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            "p99": statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values),
            "last_value": values[-1],
            "last_updated": metric_history[-1].timestamp
        }
    
    async def get_metric_stats(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get aggregate statistics for a metric."""
        async with self._lock:
            return self._aggregates.get(metric_name)
    
    async def get_recent_metrics(
        self, 
        metric_name: str, 
        duration_minutes: int = 5
    ) -> List[PerformanceMetric]:
        """Get recent metrics within time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        async with self._lock:
            if metric_name not in self._metrics:
                return []
            
            return [
                metric for metric in self._metrics[metric_name]
                if metric.timestamp > cutoff_time
            ]
    
    async def get_all_metric_names(self) -> List[str]:
        """Get all tracked metric names."""
        async with self._lock:
            return list(self._metrics.keys())


class BottleneckDetector:
    """Intelligent bottleneck detection and analysis."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize bottleneck detector."""
        self.metrics_collector = metrics_collector
        
        # Detection thresholds
        self.thresholds = {
            "cpu_usage": 70.0,          # CPU usage percentage
            "memory_usage": 80.0,       # Memory usage percentage
            "response_time": 5.0,       # Response time in seconds
            "error_rate": 5.0,          # Error rate percentage
            "queue_depth": 10,          # Queue depth
            "connection_pool_usage": 80.0  # Connection pool usage percentage
        }
        
        # Detection patterns
        self.detection_patterns = {
            BottleneckType.CPU_BOUND: self._detect_cpu_bottleneck,
            BottleneckType.MEMORY_BOUND: self._detect_memory_bottleneck,
            BottleneckType.IO_BOUND: self._detect_io_bottleneck,
            BottleneckType.RATE_LIMITED: self._detect_rate_limit_bottleneck,
            BottleneckType.CONCURRENCY_LIMITED: self._detect_concurrency_bottleneck,
            BottleneckType.RESOURCE_CONTENTION: self._detect_resource_contention
        }
        
        logger.info("BottleneckDetector initialized")
    
    async def detect_bottlenecks(self, analysis_window_minutes: int = 5) -> List[BottleneckAnalysis]:
        """Detect current performance bottlenecks."""
        bottlenecks = []
        
        logger.debug(f"Running bottleneck detection with {analysis_window_minutes} minute window")
        
        # Run all detection patterns
        for bottleneck_type, detector_func in self.detection_patterns.items():
            try:
                analysis = await detector_func(analysis_window_minutes)
                if analysis:
                    bottlenecks.append(analysis)
                    logger.info(f"Bottleneck detected: {bottleneck_type.value} (severity: {analysis.severity:.2f})")
            except Exception as e:
                logger.error(f"Error in bottleneck detection for {bottleneck_type}: {e}")
        
        # Sort by severity (highest first)
        bottlenecks.sort(key=lambda x: x.severity, reverse=True)
        
        logger.info(f"Bottleneck detection completed: {len(bottlenecks)} issues found")
        return bottlenecks
    
    async def _detect_cpu_bottleneck(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect CPU bottlenecks."""
        cpu_metrics = await self.metrics_collector.get_recent_metrics("cpu_usage", window_minutes)
        
        if not cpu_metrics:
            return None
        
        avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
        max_cpu = max(m.value for m in cpu_metrics)
        
        if avg_cpu > self.thresholds["cpu_usage"]:
            severity = min(avg_cpu / 100.0, 1.0)
            
            return BottleneckAnalysis(
                bottleneck_type=BottleneckType.CPU_BOUND,
                severity=severity,
                affected_operations=["extraction", "parsing", "analysis"],
                root_cause=f"High CPU usage: {avg_cpu:.1f}% average, {max_cpu:.1f}% peak",
                impact_description="Processing delays due to CPU saturation",
                recommendations=[
                    "Reduce concurrent extraction tasks",
                    "Optimize parsing algorithms",
                    "Consider upgrading CPU resources",
                    "Implement CPU-intensive task queuing"
                ]
            )
        
        return None
    
    async def _detect_memory_bottleneck(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect memory bottlenecks."""
        memory_metrics = await self.metrics_collector.get_recent_metrics("memory_usage", window_minutes)
        
        if not memory_metrics:
            return None
        
        avg_memory = sum(m.value for m in memory_metrics) / len(memory_metrics)
        max_memory = max(m.value for m in memory_metrics)
        
        if avg_memory > self.thresholds["memory_usage"]:
            severity = min(avg_memory / 100.0, 1.0)
            
            return BottleneckAnalysis(
                bottleneck_type=BottleneckType.MEMORY_BOUND,
                severity=severity,
                affected_operations=["crawling", "caching", "batch_processing"],
                root_cause=f"High memory usage: {avg_memory:.1f}% average, {max_memory:.1f}% peak",
                impact_description="Risk of out-of-memory errors and performance degradation",
                recommendations=[
                    "Enable memory optimization",
                    "Reduce batch sizes",
                    "Clear unused caches",
                    "Implement memory-efficient data structures"
                ]
            )
        
        return None
    
    async def _detect_io_bottleneck(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect I/O bottlenecks."""
        response_time_metrics = await self.metrics_collector.get_recent_metrics("response_time", window_minutes)
        
        if not response_time_metrics:
            return None
        
        avg_response_time = sum(m.value for m in response_time_metrics) / len(response_time_metrics)
        max_response_time = max(m.value for m in response_time_metrics)
        
        if avg_response_time > self.thresholds["response_time"]:
            severity = min(avg_response_time / 30.0, 1.0)  # Scale to 30s max
            
            return BottleneckAnalysis(
                bottleneck_type=BottleneckType.IO_BOUND,
                severity=severity,
                affected_operations=["crawling", "api_requests", "database_queries"],
                root_cause=f"Slow response times: {avg_response_time:.2f}s average, {max_response_time:.2f}s peak",
                impact_description="Network or disk I/O delays causing processing slowdowns",
                recommendations=[
                    "Optimize HTTP connection pooling",
                    "Implement request caching",
                    "Reduce request timeouts",
                    "Use CDN for static resources"
                ]
            )
        
        return None
    
    async def _detect_rate_limit_bottleneck(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect rate limiting bottlenecks."""
        error_metrics = await self.metrics_collector.get_recent_metrics("rate_limit_errors", window_minutes)
        
        if not error_metrics or len(error_metrics) == 0:
            return None
        
        error_count = len(error_metrics)
        total_requests = await self._get_total_requests(window_minutes)
        
        if total_requests > 0:
            error_rate = (error_count / total_requests) * 100
            
            if error_rate > 1.0:  # More than 1% rate limit errors
                severity = min(error_rate / 10.0, 1.0)  # Scale to 10% max
                
                return BottleneckAnalysis(
                    bottleneck_type=BottleneckType.RATE_LIMITED,
                    severity=severity,
                    affected_operations=["search", "crawling", "api_requests"],
                    root_cause=f"Rate limit violations: {error_rate:.1f}% of requests",
                    impact_description="API rate limits causing request failures and delays",
                    recommendations=[
                        "Reduce request rate",
                        "Implement exponential backoff",
                        "Use request queuing",
                        "Consider upgrading API plan"
                    ]
                )
        
        return None
    
    async def _detect_concurrency_bottleneck(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect concurrency bottlenecks."""
        queue_metrics = await self.metrics_collector.get_recent_metrics("queue_depth", window_minutes)
        
        if not queue_metrics:
            return None
        
        avg_queue_depth = sum(m.value for m in queue_metrics) / len(queue_metrics)
        max_queue_depth = max(m.value for m in queue_metrics)
        
        if avg_queue_depth > self.thresholds["queue_depth"]:
            severity = min(avg_queue_depth / 100.0, 1.0)  # Scale to 100 max
            
            return BottleneckAnalysis(
                bottleneck_type=BottleneckType.CONCURRENCY_LIMITED,
                severity=severity,
                affected_operations=["extraction", "batch_processing", "concurrent_tasks"],
                root_cause=f"High queue depth: {avg_queue_depth:.1f} average, {max_queue_depth:.1f} peak",
                impact_description="Task queues saturated, causing processing delays",
                recommendations=[
                    "Increase worker count",
                    "Optimize task processing time",
                    "Implement task prioritization",
                    "Scale horizontally"
                ]
            )
        
        return None
    
    async def _detect_resource_contention(self, window_minutes: int) -> Optional[BottleneckAnalysis]:
        """Detect resource contention bottlenecks."""
        connection_metrics = await self.metrics_collector.get_recent_metrics("connection_pool_usage", window_minutes)
        
        if not connection_metrics:
            return None
        
        avg_pool_usage = sum(m.value for m in connection_metrics) / len(connection_metrics)
        max_pool_usage = max(m.value for m in connection_metrics)
        
        if avg_pool_usage > self.thresholds["connection_pool_usage"]:
            severity = min(avg_pool_usage / 100.0, 1.0)
            
            return BottleneckAnalysis(
                bottleneck_type=BottleneckType.RESOURCE_CONTENTION,
                severity=severity,
                affected_operations=["http_requests", "database_connections", "external_apis"],
                root_cause=f"High connection pool usage: {avg_pool_usage:.1f}% average, {max_pool_usage:.1f}% peak",
                impact_description="Connection pool exhaustion causing request blocking",
                recommendations=[
                    "Increase connection pool size",
                    "Optimize connection lifecycle",
                    "Implement connection recycling",
                    "Monitor connection leaks"
                ]
            )
        
        return None
    
    async def _get_total_requests(self, window_minutes: int) -> int:
        """Get total request count for error rate calculation."""
        try:
            request_metrics = await self.metrics_collector.get_recent_metrics("total_requests", window_minutes)
            return len(request_metrics) if request_metrics else 1
        except Exception:
            return 1  # Fallback to avoid division by zero


class PerformanceOptimizer:
    """Performance optimization recommendations and automated improvements."""
    
    def __init__(self, metrics_collector: MetricsCollector, bottleneck_detector: BottleneckDetector):
        """Initialize performance optimizer."""
        self.metrics_collector = metrics_collector
        self.bottleneck_detector = bottleneck_detector
        
        # Optimization strategies
        self.optimization_strategies = {
            BottleneckType.CPU_BOUND: self._optimize_cpu_usage,
            BottleneckType.MEMORY_BOUND: self._optimize_memory_usage,
            BottleneckType.IO_BOUND: self._optimize_io_performance,
            BottleneckType.RATE_LIMITED: self._optimize_rate_limiting,
            BottleneckType.CONCURRENCY_LIMITED: self._optimize_concurrency,
            BottleneckType.RESOURCE_CONTENTION: self._optimize_resource_usage
        }
        
        logger.info("PerformanceOptimizer initialized")
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """Comprehensive performance analysis."""
        logger.info("Starting comprehensive performance analysis")
        
        # Detect bottlenecks
        bottlenecks = await self.bottleneck_detector.detect_bottlenecks()
        
        # Get key performance metrics
        key_metrics = await self._get_key_performance_metrics()
        
        # Calculate overall performance level
        performance_level = self._calculate_performance_level(key_metrics)
        
        # Generate optimization recommendations
        recommendations = await self._generate_recommendations(bottlenecks)
        
        analysis_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_level": performance_level.value,
            "key_metrics": key_metrics,
            "bottlenecks": [
                {
                    "type": b.bottleneck_type.value,
                    "severity": b.severity,
                    "root_cause": b.root_cause,
                    "impact": b.impact_description,
                    "affected_operations": b.affected_operations
                }
                for b in bottlenecks
            ],
            "optimization_recommendations": recommendations,
            "summary": {
                "total_bottlenecks": len(bottlenecks),
                "critical_issues": len([b for b in bottlenecks if b.severity > 0.8]),
                "performance_score": self._calculate_performance_score(key_metrics, bottlenecks)
            }
        }
        
        logger.info(f"Performance analysis completed: {performance_level.value} level, "
                   f"{len(bottlenecks)} bottlenecks detected")
        
        return analysis_result
    
    async def _get_key_performance_metrics(self) -> Dict[str, Any]:
        """Get key performance metrics summary."""
        metrics = {}
        
        # Response time metrics
        response_time_stats = await self.metrics_collector.get_metric_stats("response_time")
        if response_time_stats:
            metrics["response_time"] = {
                "avg": response_time_stats["avg"],
                "p95": response_time_stats["p95"],
                "p99": response_time_stats["p99"]
            }
        
        # Resource usage metrics
        cpu_stats = await self.metrics_collector.get_metric_stats("cpu_usage")
        if cpu_stats:
            metrics["cpu_usage"] = {
                "avg": cpu_stats["avg"],
                "max": cpu_stats["max"]
            }
        
        memory_stats = await self.metrics_collector.get_metric_stats("memory_usage")
        if memory_stats:
            metrics["memory_usage"] = {
                "avg": memory_stats["avg"],
                "max": memory_stats["max"]
            }
        
        # Throughput metrics
        throughput_stats = await self.metrics_collector.get_metric_stats("requests_per_second")
        if throughput_stats:
            metrics["throughput"] = {
                "avg": throughput_stats["avg"],
                "max": throughput_stats["max"]
            }
        
        # Error rate metrics
        error_stats = await self.metrics_collector.get_metric_stats("error_rate")
        if error_stats:
            metrics["error_rate"] = {
                "avg": error_stats["avg"],
                "max": error_stats["max"]
            }
        
        return metrics
    
    def _calculate_performance_level(self, key_metrics: Dict[str, Any]) -> PerformanceLevel:
        """Calculate overall performance level."""
        score = 100.0  # Start with perfect score
        
        # Response time scoring
        if "response_time" in key_metrics:
            avg_response = key_metrics["response_time"]["avg"]
            if avg_response > 30:
                score -= 50
            elif avg_response > 10:
                score -= 30
            elif avg_response > 3:
                score -= 15
            elif avg_response > 1:
                score -= 5
        
        # Resource usage scoring
        if "cpu_usage" in key_metrics:
            cpu_usage = key_metrics["cpu_usage"]["avg"]
            if cpu_usage > 95:
                score -= 25
            elif cpu_usage > 85:
                score -= 15
            elif cpu_usage > 70:
                score -= 10
        
        if "memory_usage" in key_metrics:
            memory_usage = key_metrics["memory_usage"]["avg"]
            if memory_usage > 95:
                score -= 25
            elif memory_usage > 85:
                score -= 15
            elif memory_usage > 80:
                score -= 10
        
        # Error rate scoring
        if "error_rate" in key_metrics:
            error_rate = key_metrics["error_rate"]["avg"]
            if error_rate > 10:
                score -= 30
            elif error_rate > 5:
                score -= 15
            elif error_rate > 1:
                score -= 5
        
        # Convert score to performance level
        if score >= 90:
            return PerformanceLevel.EXCELLENT
        elif score >= 75:
            return PerformanceLevel.GOOD
        elif score >= 60:
            return PerformanceLevel.ACCEPTABLE
        elif score >= 40:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _calculate_performance_score(self, key_metrics: Dict[str, Any], bottlenecks: List[BottleneckAnalysis]) -> float:
        """Calculate numerical performance score (0-100)."""
        base_score = 100.0
        
        # Deduct points for bottlenecks
        for bottleneck in bottlenecks:
            deduction = bottleneck.severity * 20  # Up to 20 points per bottleneck
            base_score -= deduction
        
        # Additional deductions for poor metrics
        if "error_rate" in key_metrics:
            error_rate = key_metrics["error_rate"]["avg"]
            base_score -= min(error_rate * 2, 20)  # Up to 20 points for errors
        
        return max(0.0, min(100.0, base_score))
    
    async def _generate_recommendations(self, bottlenecks: List[BottleneckAnalysis]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on bottlenecks."""
        recommendations = []
        
        for bottleneck in bottlenecks:
            # Get strategy-specific recommendations
            if bottleneck.bottleneck_type in self.optimization_strategies:
                try:
                    strategy_recommendations = await self.optimization_strategies[bottleneck.bottleneck_type]()
                    
                    recommendations.append({
                        "bottleneck_type": bottleneck.bottleneck_type.value,
                        "severity": bottleneck.severity,
                        "priority": "high" if bottleneck.severity > 0.7 else "medium" if bottleneck.severity > 0.4 else "low",
                        "recommendations": strategy_recommendations,
                        "automated_fixes_available": len([r for r in strategy_recommendations if r.get("automated", False)]) > 0
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating recommendations for {bottleneck.bottleneck_type}: {e}")
        
        return recommendations
    
    async def _optimize_cpu_usage(self) -> List[Dict[str, Any]]:
        """Generate CPU optimization recommendations."""
        return [
            {
                "action": "Reduce concurrent extraction tasks",
                "description": "Lower the max_concurrent_extractions setting",
                "impact": "Reduces CPU load but may increase processing time",
                "automated": True,
                "config_change": {"max_concurrent_extractions": "decrease by 2"}
            },
            {
                "action": "Enable request queuing",
                "description": "Queue requests during high load periods",
                "impact": "Smooths CPU usage spikes",
                "automated": True,
                "config_change": {"enable_request_queuing": True}
            },
            {
                "action": "Optimize parsing algorithms",
                "description": "Review and optimize HTML parsing logic",
                "impact": "Reduces CPU usage per request",
                "automated": False
            }
        ]
    
    async def _optimize_memory_usage(self) -> List[Dict[str, Any]]:
        """Generate memory optimization recommendations."""
        return [
            {
                "action": "Enable memory optimization",
                "description": "Activate automatic memory cleanup",
                "impact": "Reduces memory usage and prevents leaks",
                "automated": True,
                "config_change": {"enable_memory_optimization": True}
            },
            {
                "action": "Reduce batch sizes",
                "description": "Process smaller batches to reduce memory footprint",
                "impact": "Lower memory usage but more batch operations",
                "automated": True,
                "config_change": {"batch_size": "decrease by 25%"}
            },
            {
                "action": "Clear cache more frequently",
                "description": "Reduce cache TTL values",
                "impact": "Lower memory usage but more cache misses",
                "automated": True,
                "config_change": {"cache_ttl_reduction": "50%"}
            }
        ]
    
    async def _optimize_io_performance(self) -> List[Dict[str, Any]]:
        """Generate I/O optimization recommendations."""
        return [
            {
                "action": "Increase connection pool size",
                "description": "Allow more concurrent HTTP connections",
                "impact": "Better I/O parallelism but higher resource usage",
                "automated": True,
                "config_change": {"max_pool_size": "increase by 50%"}
            },
            {
                "action": "Reduce request timeouts",
                "description": "Set more aggressive timeout values",
                "impact": "Faster failure detection but more timeout errors",
                "automated": True,
                "config_change": {"request_timeout": "reduce by 25%"}
            },
            {
                "action": "Enable HTTP/2",
                "description": "Use HTTP/2 for better multiplexing",
                "impact": "Improved connection efficiency",
                "automated": True,
                "config_change": {"http2_enabled": True}
            }
        ]
    
    async def _optimize_rate_limiting(self) -> List[Dict[str, Any]]:
        """Generate rate limiting optimization recommendations."""
        return [
            {
                "action": "Implement exponential backoff",
                "description": "Add exponential backoff for rate limited requests",
                "impact": "Reduces rate limit violations",
                "automated": True,
                "config_change": {"exponential_backoff_enabled": True}
            },
            {
                "action": "Reduce request rate",
                "description": "Lower the rate of API requests",
                "impact": "Fewer rate limit errors but slower processing",
                "automated": True,
                "config_change": {"request_rate": "reduce by 20%"}
            },
            {
                "action": "Implement request prioritization",
                "description": "Prioritize important requests during rate limiting",
                "impact": "Better resource allocation",
                "automated": True,
                "config_change": {"request_prioritization_enabled": True}
            }
        ]
    
    async def _optimize_concurrency(self) -> List[Dict[str, Any]]:
        """Generate concurrency optimization recommendations."""
        return [
            {
                "action": "Increase worker count",
                "description": "Add more concurrent workers",
                "impact": "Higher throughput but more resource usage",
                "automated": True,
                "config_change": {"max_workers": "increase by 2"}
            },
            {
                "action": "Implement task prioritization",
                "description": "Process high-priority tasks first",
                "impact": "Better task scheduling",
                "automated": True,
                "config_change": {"task_prioritization_enabled": True}
            },
            {
                "action": "Optimize task processing time",
                "description": "Review and optimize individual task performance",
                "impact": "Faster task completion",
                "automated": False
            }
        ]
    
    async def _optimize_resource_usage(self) -> List[Dict[str, Any]]:
        """Generate resource usage optimization recommendations."""
        return [
            {
                "action": "Increase connection pool size",
                "description": "Allow more concurrent connections",
                "impact": "Reduces connection contention",
                "automated": True,
                "config_change": {"max_connections": "increase by 25%"}
            },
            {
                "action": "Implement connection recycling",
                "description": "Reuse connections more efficiently",
                "impact": "Better resource utilization",
                "automated": True,
                "config_change": {"connection_recycling_enabled": True}
            },
            {
                "action": "Monitor connection leaks",
                "description": "Enable connection leak detection",
                "impact": "Prevents resource exhaustion",
                "automated": True,
                "config_change": {"connection_leak_detection": True}
            }
        ]


class PerformanceMonitor:
    """Main performance monitoring orchestrator."""
    
    def __init__(self, metrics_history_size: int = 1000):
        """Initialize performance monitor."""
        self.metrics_collector = MetricsCollector(metrics_history_size)
        self.bottleneck_detector = BottleneckDetector(self.metrics_collector)
        self.optimizer = PerformanceOptimizer(self.metrics_collector, self.bottleneck_detector)
        
        # Monitoring configuration
        self.monitoring_interval = 60.0  # Monitor every minute
        self.alert_callbacks: List[Callable[[PerformanceAlert], Awaitable[None]]] = []
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"PerformanceMonitor initialized with {metrics_history_size} metrics history")
    
    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Performance monitoring already running")
            return
        
        logger.info("Starting performance monitoring")
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        if not self._monitoring_task or self._monitoring_task.done():
            return
        
        logger.info("Stopping performance monitoring")
        self._shutdown_event.set()
        
        try:
            await self._monitoring_task
        except asyncio.CancelledError:
            pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Performance monitoring loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Analyze current performance
                analysis = await self.optimizer.analyze_performance()
                
                # Generate alerts for critical issues
                for bottleneck in analysis.get("bottlenecks", []):
                    if bottleneck["severity"] > 0.7:  # Critical severity threshold
                        alert = PerformanceAlert(
                            alert_type="bottleneck",
                            severity="critical" if bottleneck["severity"] > 0.8 else "high",
                            message=f"{bottleneck['type']} bottleneck detected: {bottleneck['root_cause']}",
                            metric_name=bottleneck["type"],
                            current_value=bottleneck["severity"],
                            threshold_value=0.7,
                            recommendations=[rec["action"] for rec in analysis.get("optimization_recommendations", [])]
                        )
                        
                        await self._send_alert(alert)
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(30.0)  # Shorter retry interval on error
        
        logger.info("Performance monitoring loop stopped")
    
    async def _send_alert(self, alert: PerformanceAlert):
        """Send performance alert to registered callbacks."""
        logger.warning(f"Performance alert: {alert.severity} - {alert.message}")
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error sending alert to callback: {e}")
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], Awaitable[None]]):
        """Register alert callback."""
        self.alert_callbacks.append(callback)
        logger.debug("Alert callback registered")
    
    def unregister_alert_callback(self, callback: Callable[[PerformanceAlert], Awaitable[None]]):
        """Unregister alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            logger.debug("Alert callback unregistered")
    
    # Public interface methods
    async def record_metric(self, name: str, value: float, unit: str, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        await self.metrics_collector.record_metric(metric)
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return await self.optimizer.analyze_performance()
    
    async def get_metric_statistics(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific metric."""
        return await self.metrics_collector.get_metric_stats(metric_name)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get performance monitoring health status."""
        return {
            "monitoring_active": not self._shutdown_event.is_set(),
            "metrics_collected": len(await self.metrics_collector.get_all_metric_names()),
            "monitoring_interval_seconds": self.monitoring_interval,
            "alert_callbacks_registered": len(self.alert_callbacks)
        }


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


async def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        await _performance_monitor.start_monitoring()
    
    return _performance_monitor


async def cleanup_performance_monitor():
    """Cleanup global performance monitor."""
    global _performance_monitor
    
    if _performance_monitor:
        await _performance_monitor.stop_monitoring()
        _performance_monitor = None