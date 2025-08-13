#!/usr/bin/env python3
"""
Production Monitoring and Health Check Example

This example demonstrates how to monitor the Company Information Extraction API
in production environments, including health checks, performance monitoring,
and alert generation.

Usage:
    python examples/example_monitoring_production.py
"""

import asyncio
import sys
import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
MONITORING_INTERVAL = 60  # seconds
ALERT_THRESHOLDS = {
    "response_time_warning": 5.0,  # seconds
    "response_time_critical": 10.0,  # seconds
    "error_rate_warning": 0.05,  # 5%
    "error_rate_critical": 0.10,  # 10%
    "queue_size_warning": 50,
    "queue_size_critical": 100
}


@dataclass
class HealthCheckResult:
    """Health check result data structure."""
    timestamp: datetime
    service: str
    status: str
    response_time: float
    details: Dict[str, Any]
    is_healthy: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "status": self.status,
            "response_time": self.response_time,
            "details": self.details,
            "is_healthy": self.is_healthy
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    avg_response_time: float
    error_rate: float
    request_count: int
    queue_size: int
    cache_hit_rate: Optional[float]
    active_extractions: int
    system_load: Optional[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "avg_response_time": self.avg_response_time,
            "error_rate": self.error_rate,
            "request_count": self.request_count,
            "queue_size": self.queue_size,
            "cache_hit_rate": self.cache_hit_rate,
            "active_extractions": self.active_extractions,
            "system_load": self.system_load
        }


class ProductionMonitor:
    """Production monitoring system for the Company Extraction API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.health_history: List[HealthCheckResult] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.alert_history: List[Dict[str, Any]] = []
    
    async def health_check_basic(self) -> HealthCheckResult:
        """Perform basic health check."""
        start_time = time.time()
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            try:
                response = await client.get("/api/v1/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="basic_health",
                        status="healthy",
                        response_time=response_time,
                        details=data,
                        is_healthy=True
                    )
                else:
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="basic_health",
                        status=f"unhealthy_http_{response.status_code}",
                        response_time=response_time,
                        details={"status_code": response.status_code, "text": response.text},
                        is_healthy=False
                    )
                    
            except Exception as e:
                response_time = time.time() - start_time
                return HealthCheckResult(
                    timestamp=datetime.now(),
                    service="basic_health",
                    status="error",
                    response_time=response_time,
                    details={"error": str(e)},
                    is_healthy=False
                )
    
    async def health_check_detailed(self) -> HealthCheckResult:
        """Perform detailed health check with dependencies."""
        start_time = time.time()
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60) as client:
            try:
                response = await client.get("/api/v1/health/detailed")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if all dependencies are healthy
                    dependencies = data.get("dependencies", {})
                    all_healthy = all(
                        dep.get("status") == "healthy" 
                        for dep in dependencies.values()
                    )
                    
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="detailed_health",
                        status="healthy" if all_healthy else "degraded",
                        response_time=response_time,
                        details=data,
                        is_healthy=all_healthy
                    )
                else:
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="detailed_health",
                        status=f"unhealthy_http_{response.status_code}",
                        response_time=response_time,
                        details={"status_code": response.status_code},
                        is_healthy=False
                    )
                    
            except Exception as e:
                response_time = time.time() - start_time
                return HealthCheckResult(
                    timestamp=datetime.now(),
                    service="detailed_health",
                    status="error",
                    response_time=response_time,
                    details={"error": str(e)},
                    is_healthy=False
                )
    
    async def health_check_company_service(self) -> HealthCheckResult:
        """Health check for company extraction service specifically."""
        start_time = time.time()
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60) as client:
            try:
                response = await client.get("/api/v1/company/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="company_service",
                        status="healthy",
                        response_time=response_time,
                        details=data,
                        is_healthy=True
                    )
                else:
                    return HealthCheckResult(
                        timestamp=datetime.now(),
                        service="company_service",
                        status=f"unhealthy_http_{response.status_code}",
                        response_time=response_time,
                        details={"status_code": response.status_code},
                        is_healthy=False
                    )
                    
            except Exception as e:
                response_time = time.time() - start_time
                return HealthCheckResult(
                    timestamp=datetime.now(),
                    service="company_service",
                    status="error",
                    response_time=response_time,
                    details={"error": str(e)},
                    is_healthy=False
                )
    
    async def get_performance_metrics(self) -> Optional[PerformanceMetrics]:
        """Get current performance metrics."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            try:
                # Get batch processing statistics
                response = await client.get("/api/v1/company/batch/stats")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return PerformanceMetrics(
                        timestamp=datetime.now(),
                        avg_response_time=data.get("avg_response_time", 0.0),
                        error_rate=data.get("error_rate", 0.0),
                        request_count=data.get("request_count", 0),
                        queue_size=data.get("queue_size", 0),
                        cache_hit_rate=data.get("cache_hit_rate"),
                        active_extractions=data.get("active_extractions", 0),
                        system_load=data.get("system_load")
                    )
                else:
                    logger.warning(f"Failed to get performance metrics: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting performance metrics: {e}")
                return None
    
    async def run_comprehensive_health_check(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks and return results."""
        logger.info("Running comprehensive health checks...")
        
        # Run all health checks concurrently
        basic_task = self.health_check_basic()
        detailed_task = self.health_check_detailed()
        company_task = self.health_check_company_service()
        
        basic_result, detailed_result, company_result = await asyncio.gather(
            basic_task, detailed_task, company_task, return_exceptions=True
        )
        
        results = {}
        
        # Handle results and exceptions
        if isinstance(basic_result, HealthCheckResult):
            results["basic"] = basic_result
            self.health_history.append(basic_result)
        else:
            logger.error(f"Basic health check failed: {basic_result}")
        
        if isinstance(detailed_result, HealthCheckResult):
            results["detailed"] = detailed_result
            self.health_history.append(detailed_result)
        else:
            logger.error(f"Detailed health check failed: {detailed_result}")
        
        if isinstance(company_result, HealthCheckResult):
            results["company"] = company_result
            self.health_history.append(company_result)
        else:
            logger.error(f"Company health check failed: {company_result}")
        
        return results
    
    def check_alert_conditions(
        self, 
        health_results: Dict[str, HealthCheckResult], 
        performance_metrics: Optional[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """Check for alert conditions and return alerts."""
        alerts = []
        
        # Check health results
        for service, result in health_results.items():
            if not result.is_healthy:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "health_check_failed",
                    "severity": "critical",
                    "service": service,
                    "message": f"Health check failed for {service}: {result.status}",
                    "details": result.details
                }
                alerts.append(alert)
            
            # Check response time
            if result.response_time > ALERT_THRESHOLDS["response_time_critical"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "slow_response_time",
                    "severity": "critical",
                    "service": service,
                    "message": f"Critical response time for {service}: {result.response_time:.2f}s",
                    "details": {"response_time": result.response_time}
                }
                alerts.append(alert)
            elif result.response_time > ALERT_THRESHOLDS["response_time_warning"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "slow_response_time",
                    "severity": "warning",
                    "service": service,
                    "message": f"Slow response time for {service}: {result.response_time:.2f}s",
                    "details": {"response_time": result.response_time}
                }
                alerts.append(alert)
        
        # Check performance metrics
        if performance_metrics:
            # Error rate alerts
            if performance_metrics.error_rate > ALERT_THRESHOLDS["error_rate_critical"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "high_error_rate",
                    "severity": "critical",
                    "service": "api",
                    "message": f"Critical error rate: {performance_metrics.error_rate:.1%}",
                    "details": {"error_rate": performance_metrics.error_rate}
                }
                alerts.append(alert)
            elif performance_metrics.error_rate > ALERT_THRESHOLDS["error_rate_warning"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "high_error_rate",
                    "severity": "warning",
                    "service": "api",
                    "message": f"Elevated error rate: {performance_metrics.error_rate:.1%}",
                    "details": {"error_rate": performance_metrics.error_rate}
                }
                alerts.append(alert)
            
            # Queue size alerts
            if performance_metrics.queue_size > ALERT_THRESHOLDS["queue_size_critical"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "large_queue_size",
                    "severity": "critical",
                    "service": "batch_processor",
                    "message": f"Critical queue size: {performance_metrics.queue_size}",
                    "details": {"queue_size": performance_metrics.queue_size}
                }
                alerts.append(alert)
            elif performance_metrics.queue_size > ALERT_THRESHOLDS["queue_size_warning"]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "large_queue_size",
                    "severity": "warning",
                    "service": "batch_processor",
                    "message": f"Large queue size: {performance_metrics.queue_size}",
                    "details": {"queue_size": performance_metrics.queue_size}
                }
                alerts.append(alert)
        
        return alerts
    
    def log_monitoring_summary(
        self, 
        health_results: Dict[str, HealthCheckResult], 
        performance_metrics: Optional[PerformanceMetrics],
        alerts: List[Dict[str, Any]]
    ):
        """Log monitoring summary."""
        logger.info("=" * 60)
        logger.info("MONITORING SUMMARY")
        logger.info("=" * 60)
        
        # Health status
        logger.info("Health Status:")
        for service, result in health_results.items():
            status_icon = "✅" if result.is_healthy else "❌"
            logger.info(f"  {status_icon} {service}: {result.status} ({result.response_time:.2f}s)")
        
        # Performance metrics
        if performance_metrics:
            logger.info("Performance Metrics:")
            logger.info(f"  Avg Response Time: {performance_metrics.avg_response_time:.2f}s")
            logger.info(f"  Error Rate: {performance_metrics.error_rate:.1%}")
            logger.info(f"  Request Count: {performance_metrics.request_count}")
            logger.info(f"  Queue Size: {performance_metrics.queue_size}")
            logger.info(f"  Active Extractions: {performance_metrics.active_extractions}")
            
            if performance_metrics.cache_hit_rate is not None:
                logger.info(f"  Cache Hit Rate: {performance_metrics.cache_hit_rate:.1%}")
        
        # Alerts
        if alerts:
            logger.warning(f"Active Alerts ({len(alerts)}):")
            for alert in alerts:
                severity_icon = "🚨" if alert["severity"] == "critical" else "⚠️"
                logger.warning(f"  {severity_icon} {alert['message']}")
        else:
            logger.info("No active alerts")
        
        logger.info("=" * 60)
    
    async def send_alert_notification(self, alert: Dict[str, Any]):
        """Send alert notification (email, Slack, etc.)."""
        # This is a simplified example - in production you'd integrate with
        # your actual alerting system (PagerDuty, Slack, etc.)
        
        logger.warning(f"ALERT: {alert['message']}")
        
        # Example: Send to Slack webhook (if configured)
        slack_webhook = "YOUR_SLACK_WEBHOOK_URL"  # Replace with actual webhook
        
        if slack_webhook and slack_webhook != "YOUR_SLACK_WEBHOOK_URL":
            try:
                emoji = "🚨" if alert["severity"] == "critical" else "⚠️"
                message = f"{emoji} *{alert['type']}*\n{alert['message']}\nService: {alert['service']}"
                
                async with httpx.AsyncClient() as client:
                    await client.post(
                        slack_webhook,
                        json={"text": message}
                    )
                    
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
    
    async def run_monitoring_cycle(self):
        """Run one complete monitoring cycle."""
        logger.info("Starting monitoring cycle...")
        
        # Run health checks
        health_results = await self.run_comprehensive_health_check()
        
        # Get performance metrics
        performance_metrics = await self.get_performance_metrics()
        if performance_metrics:
            self.performance_history.append(performance_metrics)
        
        # Check for alerts
        alerts = self.check_alert_conditions(health_results, performance_metrics)
        
        # Send alert notifications
        for alert in alerts:
            await self.send_alert_notification(alert)
            self.alert_history.append(alert)
        
        # Log summary
        self.log_monitoring_summary(health_results, performance_metrics, alerts)
        
        # Cleanup old history (keep last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        self.health_history = [
            h for h in self.health_history 
            if h.timestamp > cutoff_time
        ]
        
        self.performance_history = [
            p for p in self.performance_history 
            if p.timestamp > cutoff_time
        ]
        
        self.alert_history = [
            a for a in self.alert_history 
            if datetime.fromisoformat(a["timestamp"]) > cutoff_time
        ]
    
    def export_monitoring_data(self, filename: str):
        """Export monitoring data to JSON file."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "health_history": [h.to_dict() for h in self.health_history],
            "performance_history": [p.to_dict() for p in self.performance_history],
            "alert_history": self.alert_history
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Monitoring data exported to {filename}")


async def run_continuous_monitoring():
    """Run continuous monitoring."""
    monitor = ProductionMonitor()
    
    logger.info("Starting continuous monitoring...")
    logger.info(f"Monitoring interval: {MONITORING_INTERVAL} seconds")
    
    try:
        while True:
            await monitor.run_monitoring_cycle()
            
            # Export data periodically (every hour)
            if len(monitor.health_history) % 60 == 0:  # Approximately every hour
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                monitor.export_monitoring_data(f"monitoring_data_{timestamp}.json")
            
            await asyncio.sleep(MONITORING_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        
        # Export final data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        monitor.export_monitoring_data(f"monitoring_data_final_{timestamp}.json")


async def run_single_check():
    """Run a single monitoring check."""
    monitor = ProductionMonitor()
    await monitor.run_monitoring_cycle()
    
    # Export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    monitor.export_monitoring_data(f"monitoring_check_{timestamp}.json")


async def run_performance_baseline():
    """Establish performance baseline by running multiple checks."""
    logger.info("Establishing performance baseline...")
    
    monitor = ProductionMonitor()
    baseline_checks = 10
    
    for i in range(baseline_checks):
        logger.info(f"Baseline check {i+1}/{baseline_checks}")
        await monitor.run_monitoring_cycle()
        await asyncio.sleep(30)  # 30-second intervals
    
    # Calculate baseline metrics
    if monitor.performance_history:
        response_times = [p.avg_response_time for p in monitor.performance_history]
        error_rates = [p.error_rate for p in monitor.performance_history]
        
        avg_response_time = sum(response_times) / len(response_times)
        avg_error_rate = sum(error_rates) / len(error_rates)
        
        logger.info("Performance Baseline Established:")
        logger.info(f"  Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"  Average Error Rate: {avg_error_rate:.1%}")
        
        # Export baseline data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        monitor.export_monitoring_data(f"performance_baseline_{timestamp}.json")


def main():
    """Main function."""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "continuous":
            asyncio.run(run_continuous_monitoring())
        elif mode == "single":
            asyncio.run(run_single_check())
        elif mode == "baseline":
            asyncio.run(run_performance_baseline())
        else:
            print("Usage: python example_monitoring_production.py [continuous|single|baseline]")
            sys.exit(1)
    else:
        # Default: run single check
        asyncio.run(run_single_check())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        sys.exit(1)