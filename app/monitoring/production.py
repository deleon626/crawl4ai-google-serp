"""
Production monitoring and alerting system.

This module implements real-time system health monitoring, alerting for security incidents,
performance degradation detection, resource usage tracking, and SLA monitoring.
"""

import asyncio
import logging
import psutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from uuid import uuid4

import aioredis
from fastapi import Request, Response
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class HealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class Metric(BaseModel):
    """Individual metric data point."""
    
    name: str = Field(description="Metric name")
    value: float = Field(description="Metric value")
    metric_type: MetricType = Field(description="Type of metric")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metric timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    unit: Optional[str] = Field(default=None, description="Metric unit")


class Alert(BaseModel):
    """Alert notification."""
    
    alert_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique alert ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Alert timestamp")
    severity: AlertSeverity = Field(description="Alert severity")
    title: str = Field(description="Alert title")
    description: str = Field(description="Alert description")
    source: str = Field(description="Alert source system/component")
    metric_name: Optional[str] = Field(default=None, description="Related metric name")
    current_value: Optional[float] = Field(default=None, description="Current metric value")
    threshold_value: Optional[float] = Field(default=None, description="Threshold that was breached")
    tags: Dict[str, str] = Field(default_factory=dict, description="Alert tags")
    resolved: bool = Field(default=False, description="Whether alert is resolved")
    resolved_at: Optional[datetime] = Field(default=None, description="When alert was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution notes")


class HealthCheck(BaseModel):
    """Health check result."""
    
    component: str = Field(description="Component name")
    status: HealthStatus = Field(description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: float = Field(description="Response time in milliseconds")
    details: Dict = Field(default_factory=dict, description="Additional health details")
    error_message: Optional[str] = Field(default=None, description="Error message if unhealthy")


class SLATarget(BaseModel):
    """Service Level Agreement target."""
    
    name: str = Field(description="SLA target name")
    description: str = Field(description="SLA description")
    target_value: float = Field(description="Target value (e.g., 99.9 for 99.9% uptime)")
    measurement_window_hours: int = Field(description="Measurement window in hours")
    metric_name: str = Field(description="Metric to measure against")
    threshold_type: str = Field(description="above or below threshold")
    alert_threshold: float = Field(description="Alert when SLA is at risk")


class SLAStatus(BaseModel):
    """Current SLA status."""
    
    target: SLATarget = Field(description="SLA target definition")
    current_value: float = Field(description="Current measured value")
    status: str = Field(description="meeting, at_risk, or breach")
    window_start: datetime = Field(description="Measurement window start")
    window_end: datetime = Field(description="Measurement window end")
    breach_duration_minutes: float = Field(default=0.0, description="Total breach duration in window")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class SystemMetrics(BaseModel):
    """System resource metrics."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float = Field(description="CPU usage percentage")
    memory_percent: float = Field(description="Memory usage percentage")
    memory_available_mb: float = Field(description="Available memory in MB")
    disk_usage_percent: float = Field(description="Disk usage percentage")
    disk_free_gb: float = Field(description="Free disk space in GB")
    network_bytes_sent: int = Field(description="Network bytes sent")
    network_bytes_recv: int = Field(description="Network bytes received")
    open_connections: int = Field(description="Number of open network connections")
    load_average: List[float] = Field(description="System load average (1, 5, 15 minutes)")


class ProductionMonitor:
    """Main production monitoring system."""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.alerts: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.sla_targets: Dict[str, SLATarget] = {}
        self.sla_status: Dict[str, SLAStatus] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.redis: Optional[aioredis.Redis] = None
        
        # Monitoring configuration
        self.collection_interval = 30  # seconds
        self.alert_cooldown = 300  # 5 minutes
        self.last_alerts: Dict[str, datetime] = {}
        self.max_alerts_memory = 10000
        
        # System thresholds
        self.thresholds = {
            "cpu_percent": {"warning": 70.0, "critical": 85.0},
            "memory_percent": {"warning": 80.0, "critical": 90.0},
            "disk_usage_percent": {"warning": 80.0, "critical": 90.0},
            "response_time_ms": {"warning": 1000.0, "critical": 5000.0},
            "error_rate_percent": {"warning": 1.0, "critical": 5.0},
            "request_rate_per_minute": {"warning": 1000, "critical": 2000}
        }
        
        # Initialize default SLA targets
        self._setup_default_slas()
        
        # Start background monitoring
        self._monitoring_task = None
    
    def _setup_default_slas(self):
        """Setup default SLA targets."""
        sla_targets = [
            SLATarget(
                name="api_availability",
                description="API availability - percentage of successful requests",
                target_value=99.9,
                measurement_window_hours=24,
                metric_name="request_success_rate",
                threshold_type="above",
                alert_threshold=99.0
            ),
            SLATarget(
                name="response_time",
                description="95th percentile response time under 1000ms",
                target_value=1000.0,
                measurement_window_hours=1,
                metric_name="response_time_p95",
                threshold_type="below",
                alert_threshold=1500.0
            ),
            SLATarget(
                name="error_rate",
                description="Error rate below 1%",
                target_value=1.0,
                measurement_window_hours=1,
                metric_name="error_rate_percent",
                threshold_type="below",
                alert_threshold=2.0
            ),
            SLATarget(
                name="system_availability",
                description="System uptime above 99.9%",
                target_value=99.9,
                measurement_window_hours=24,
                metric_name="uptime_percent",
                threshold_type="above",
                alert_threshold=99.5
            )
        ]
        
        for target in sla_targets:
            self.sla_targets[target.name] = target
            self.sla_status[target.name] = SLAStatus(
                target=target,
                current_value=0.0,
                status="unknown",
                window_start=datetime.utcnow() - timedelta(hours=target.measurement_window_hours),
                window_end=datetime.utcnow()
            )
    
    async def initialize(self):
        """Initialize monitoring system."""
        try:
            self.redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis for monitoring data")
        except Exception as e:
            logger.warning(f"Redis not available for monitoring persistence: {e}")
        
        # Start background monitoring
        self._monitoring_task = asyncio.create_task(self._background_monitoring())
        logger.info("Production monitoring system initialized")
    
    async def shutdown(self):
        """Shutdown monitoring system."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Production monitoring system shutdown complete")
    
    async def record_metric(self, name: str, value: float, metric_type: MetricType,
                          labels: Dict[str, str] = None, unit: str = None):
        """Record a metric value."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            unit=unit
        )
        
        # Store in memory
        self.metrics[name].append(metric)
        
        # Persist to Redis if available
        if self.redis:
            await self.redis.lpush(
                f"metrics:{name}",
                metric.json()
            )
            await self.redis.expire(f"metrics:{name}", 86400)  # 24 hours
        
        # Check thresholds and generate alerts
        await self._check_metric_thresholds(metric)
    
    async def _check_metric_thresholds(self, metric: Metric):
        """Check if metric value exceeds thresholds."""
        thresholds = self.thresholds.get(metric.name)
        if not thresholds:
            return
        
        severity = None
        threshold_value = None
        
        if metric.value >= thresholds.get("critical", float('inf')):
            severity = AlertSeverity.CRITICAL
            threshold_value = thresholds["critical"]
        elif metric.value >= thresholds.get("warning", float('inf')):
            severity = AlertSeverity.WARNING
            threshold_value = thresholds["warning"]
        
        if severity:
            # Check alert cooldown
            alert_key = f"{metric.name}:{severity}"
            last_alert = self.last_alerts.get(alert_key)
            
            if not last_alert or (datetime.utcnow() - last_alert).seconds > self.alert_cooldown:
                await self._create_alert(
                    severity=severity,
                    title=f"Metric threshold exceeded: {metric.name}",
                    description=f"{metric.name} value {metric.value} exceeded {severity} threshold {threshold_value}",
                    source="monitoring_system",
                    metric_name=metric.name,
                    current_value=metric.value,
                    threshold_value=threshold_value
                )
                
                self.last_alerts[alert_key] = datetime.utcnow()
    
    async def _create_alert(self, severity: AlertSeverity, title: str, description: str,
                          source: str, metric_name: str = None, current_value: float = None,
                          threshold_value: float = None, tags: Dict[str, str] = None):
        """Create and send alert."""
        alert = Alert(
            severity=severity,
            title=title,
            description=description,
            source=source,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            tags=tags or {}
        )
        
        # Store alert
        self.alerts.append(alert)
        
        # Keep memory usage reasonable
        if len(self.alerts) > self.max_alerts_memory:
            self.alerts = self.alerts[-self.max_alerts_memory // 2:]
        
        # Persist to Redis
        if self.redis:
            await self.redis.lpush("monitoring:alerts", alert.json())
            await self.redis.expire("monitoring:alerts", 604800)  # 7 days
        
        # Send to alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert) if asyncio.iscoroutinefunction(handler) else handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        # Log alert
        level_map = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }
        logger.log(level_map[severity], f"ALERT: {title} - {description}")
    
    async def register_health_check(self, component: str, check_function: Callable) -> HealthCheck:
        """Register and run health check for a component."""
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(check_function):
                result = await check_function()
            else:
                result = check_function()
            
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, dict):
                status = HealthStatus(result.get("status", "healthy"))
                details = result.get("details", {})
                error_message = result.get("error")
            else:
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                details = {}
                error_message = None
            
            health_check = HealthCheck(
                component=component,
                status=status,
                response_time_ms=response_time,
                details=details,
                error_message=error_message
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                component=component,
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                details={"exception": str(e)},
                error_message=str(e)
            )
        
        self.health_checks[component] = health_check
        
        # Record metrics
        await self.record_metric(
            f"health_check_response_time_{component}",
            health_check.response_time_ms,
            MetricType.TIMER,
            {"component": component}
        )
        
        await self.record_metric(
            f"health_check_status_{component}",
            1.0 if health_check.status == HealthStatus.HEALTHY else 0.0,
            MetricType.GAUGE,
            {"component": component, "status": health_check.status}
        )
        
        # Generate alerts for unhealthy components
        if health_check.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
            severity = AlertSeverity.CRITICAL if health_check.status == HealthStatus.CRITICAL else AlertSeverity.ERROR
            
            await self._create_alert(
                severity=severity,
                title=f"Health check failed: {component}",
                description=f"Component {component} is {health_check.status}: {health_check.error_message or 'No details available'}",
                source="health_check_system",
                tags={"component": component, "status": health_check.status}
            )
        
        return health_check
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # Connection count
            connections = psutil.net_connections()
            open_connections = len([c for c in connections if c.status == 'ESTABLISHED'])
            
            # Load average (Unix-like systems only)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]  # Windows doesn't have load average
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                open_connections=open_connections,
                load_average=load_average
            )
            
            # Record individual metrics
            await self.record_metric("cpu_percent", cpu_percent, MetricType.GAUGE, unit="percent")
            await self.record_metric("memory_percent", memory_percent, MetricType.GAUGE, unit="percent")
            await self.record_metric("disk_usage_percent", disk_usage_percent, MetricType.GAUGE, unit="percent")
            await self.record_metric("open_connections", open_connections, MetricType.GAUGE)
            
            return metrics
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return None
    
    async def _background_monitoring(self):
        """Background task for continuous monitoring."""
        logger.info("Starting background monitoring loop")
        
        while True:
            try:
                # Collect system metrics
                system_metrics = await self._collect_system_metrics()
                
                if system_metrics and self.redis:
                    await self.redis.lpush("monitoring:system_metrics", system_metrics.json())
                    await self.redis.ltrim("monitoring:system_metrics", 0, 10000)
                
                # Update SLA status
                await self._update_sla_status()
                
                # Cleanup old data
                await self._cleanup_old_data()
                
                # Wait for next collection
                await asyncio.sleep(self.collection_interval)
            
            except asyncio.CancelledError:
                logger.info("Background monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _update_sla_status(self):
        """Update SLA status for all targets."""
        now = datetime.utcnow()
        
        for sla_name, target in self.sla_targets.items():
            try:
                # Get metrics for the measurement window
                window_start = now - timedelta(hours=target.measurement_window_hours)
                metric_values = []
                
                if target.metric_name in self.metrics:
                    for metric in self.metrics[target.metric_name]:
                        if metric.timestamp >= window_start:
                            metric_values.append(metric.value)
                
                if not metric_values:
                    continue  # No data available
                
                # Calculate current value based on metric
                if target.metric_name.endswith("_percent") or target.metric_name.endswith("_rate"):
                    current_value = sum(metric_values) / len(metric_values)
                elif target.metric_name.startswith("response_time"):
                    current_value = sorted(metric_values)[int(len(metric_values) * 0.95)]  # 95th percentile
                else:
                    current_value = sum(metric_values) / len(metric_values)
                
                # Determine status
                if target.threshold_type == "above":
                    if current_value >= target.target_value:
                        status = "meeting"
                    elif current_value >= target.alert_threshold:
                        status = "at_risk"
                    else:
                        status = "breach"
                else:  # below
                    if current_value <= target.target_value:
                        status = "meeting"
                    elif current_value <= target.alert_threshold:
                        status = "at_risk"
                    else:
                        status = "breach"
                
                # Update SLA status
                self.sla_status[sla_name] = SLAStatus(
                    target=target,
                    current_value=current_value,
                    status=status,
                    window_start=window_start,
                    window_end=now,
                    last_updated=now
                )
                
                # Generate alerts for SLA violations
                if status == "breach":
                    await self._create_alert(
                        severity=AlertSeverity.CRITICAL,
                        title=f"SLA breach: {target.name}",
                        description=f"SLA '{target.description}' is in breach. Current: {current_value:.2f}, Target: {target.target_value}",
                        source="sla_monitoring",
                        metric_name=target.metric_name,
                        current_value=current_value,
                        threshold_value=target.target_value,
                        tags={"sla": sla_name, "status": status}
                    )
                elif status == "at_risk":
                    await self._create_alert(
                        severity=AlertSeverity.WARNING,
                        title=f"SLA at risk: {target.name}",
                        description=f"SLA '{target.description}' is at risk. Current: {current_value:.2f}, Target: {target.target_value}",
                        source="sla_monitoring",
                        metric_name=target.metric_name,
                        current_value=current_value,
                        threshold_value=target.target_value,
                        tags={"sla": sla_name, "status": status}
                    )
            
            except Exception as e:
                logger.error(f"Failed to update SLA status for {sla_name}: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Clean up old metrics
        for metric_name, metric_queue in self.metrics.items():
            while metric_queue and metric_queue[0].timestamp < cutoff_time:
                metric_queue.popleft()
        
        # Clean up old health checks
        for component, health_check in list(self.health_checks.items()):
            if health_check.timestamp < cutoff_time:
                del self.health_checks[component]
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add custom alert handler."""
        self.alert_handlers.append(handler)
    
    def get_system_health(self) -> Dict:
        """Get overall system health summary."""
        now = datetime.utcnow()
        
        # Count health checks by status
        health_summary = {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "critical": 0
        }
        
        for health_check in self.health_checks.values():
            health_summary[health_check.status] += 1
        
        # Get recent alerts
        recent_alerts = [
            a for a in self.alerts 
            if (now - a.timestamp).total_seconds() < 3600  # Last hour
        ]
        
        # Overall system status
        if health_summary["critical"] > 0:
            overall_status = HealthStatus.CRITICAL
        elif health_summary["unhealthy"] > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif health_summary["degraded"] > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "timestamp": now.isoformat(),
            "overall_status": overall_status,
            "components": health_summary,
            "total_components": len(self.health_checks),
            "recent_alerts": len(recent_alerts),
            "active_metrics": len(self.metrics),
            "sla_status": {
                name: {
                    "status": status.status,
                    "current_value": status.current_value,
                    "target_value": status.target.target_value
                }
                for name, status in self.sla_status.items()
            }
        }
    
    def get_alerts(self, severity: AlertSeverity = None, limit: int = 100) -> List[Alert]:
        """Get recent alerts."""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_metrics(self, metric_name: str, limit: int = 1000) -> List[Metric]:
        """Get recent metrics for a specific metric name."""
        if metric_name not in self.metrics:
            return []
        
        metrics = list(self.metrics[metric_name])
        return sorted(metrics, key=lambda m: m.timestamp, reverse=True)[:limit]


# Global production monitor instance
production_monitor = ProductionMonitor()


# Default alert handlers
async def log_alert_handler(alert: Alert):
    """Default alert handler that logs to application logs."""
    level_map = {
        AlertSeverity.INFO: logging.INFO,
        AlertSeverity.WARNING: logging.WARNING,
        AlertSeverity.ERROR: logging.ERROR,
        AlertSeverity.CRITICAL: logging.CRITICAL
    }
    
    logger.log(
        level_map[alert.severity],
        f"PRODUCTION ALERT [{alert.severity}] {alert.title}: {alert.description}"
    )


async def console_alert_handler(alert: Alert):
    """Console alert handler for development."""
    if alert.severity in (AlertSeverity.ERROR, AlertSeverity.CRITICAL):
        print(f"\n🚨 ALERT [{alert.severity}] {alert.title}")
        print(f"   {alert.description}")
        if alert.current_value and alert.threshold_value:
            print(f"   Current: {alert.current_value}, Threshold: {alert.threshold_value}")
        print()


# Register default handlers
production_monitor.add_alert_handler(log_alert_handler)

if settings.debug:
    production_monitor.add_alert_handler(console_alert_handler)


async def monitoring_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Record metrics
        await production_monitor.record_metric(
            "request_response_time",
            response_time,
            MetricType.TIMER,
            {
                "endpoint": str(request.url.path),
                "method": request.method,
                "status_code": str(response.status_code)
            },
            "milliseconds"
        )
        
        await production_monitor.record_metric(
            "request_count",
            1,
            MetricType.COUNTER,
            {
                "endpoint": str(request.url.path),
                "method": request.method,
                "status_code": str(response.status_code)
            }
        )
        
        # Add response headers
        response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
        
        return response
    
    except Exception as e:
        # Record error metrics
        response_time = (time.time() - start_time) * 1000
        
        await production_monitor.record_metric(
            "request_error_count",
            1,
            MetricType.COUNTER,
            {
                "endpoint": str(request.url.path),
                "method": request.method,
                "error_type": type(e).__name__
            }
        )
        
        await production_monitor.record_metric(
            "request_response_time",
            response_time,
            MetricType.TIMER,
            {
                "endpoint": str(request.url.path),
                "method": request.method,
                "status_code": "error"
            },
            "milliseconds"
        )
        
        raise