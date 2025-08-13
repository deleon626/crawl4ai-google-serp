# Monitoring Guide

Comprehensive monitoring setup and procedures for the Company Information Extraction API to ensure optimal performance, reliability, and early issue detection.

## Overview

This guide covers:
- **Health Check Systems**: Application and service health monitoring
- **Metrics Collection**: Performance, business, and system metrics
- **Alerting**: Intelligent alerting with escalation procedures
- **Dashboards**: Visualization and reporting
- **Log Management**: Centralized logging and analysis

## Health Check Systems

### Application Health Checks

The API provides multiple health check endpoints with increasing levels of detail:

#### Basic Health Check
```bash
GET /api/v1/health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": "2d 14h 23m"
}
```

#### Detailed Health Check
```bash
GET /api/v1/health/detailed

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": "2d 14h 23m",
  "services": {
    "redis": {
      "status": "healthy",
      "response_time": "2ms",
      "memory_usage": "45%"
    },
    "bright_data_api": {
      "status": "healthy",
      "response_time": "156ms",
      "success_rate": "98.5%"
    },
    "crawl4ai": {
      "status": "healthy",
      "active_sessions": 3,
      "success_rate": "94.2%"
    }
  },
  "resources": {
    "cpu_usage": "34.2%",
    "memory_usage": "67.8%",
    "disk_usage": "23.1%",
    "active_connections": 12
  },
  "metrics": {
    "requests_per_minute": 23,
    "average_response_time": "18.4s",
    "error_rate": "0.3%",
    "cache_hit_rate": "76.2%"
  }
}
```

#### Company Service Health
```bash
GET /api/v1/company/health

Response:
{
  "status": "healthy",
  "capabilities": {
    "extraction_modes": ["basic", "standard", "comprehensive", "contact_focused", "financial_focused"],
    "max_concurrent_extractions": 10,
    "batch_processing_enabled": true,
    "caching_enabled": true
  },
  "performance": {
    "average_extraction_time": {
      "basic": "18.2s",
      "standard": "34.7s",
      "comprehensive": "67.3s"
    },
    "success_rates": {
      "overall": "94.7%",
      "by_mode": {
        "basic": "97.2%",
        "standard": "94.1%",
        "comprehensive": "91.8%"
      }
    }
  },
  "resource_usage": {
    "active_extractions": 3,
    "queued_requests": 0,
    "cache_size": "234MB",
    "memory_usage": "512MB"
  }
}
```

### Health Check Implementation

#### Custom Health Check Service
```python
# health_check_service.py
import asyncio
import time
import psutil
import redis
import httpx
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ServiceStatus:
    status: str  # healthy, degraded, unhealthy
    response_time: float
    details: Dict[str, Any] = None
    last_checked: datetime = None

class HealthCheckService:
    def __init__(self, config):
        self.config = config
        self.redis = redis.from_url(config.REDIS_URL)
        self.startup_time = datetime.utcnow()
        self._cache = {}
        self._cache_ttl = 30  # Cache health checks for 30 seconds
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        
        cache_key = "health_check_comprehensive"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Run all health checks concurrently
        tasks = {
            "redis": self._check_redis_health(),
            "external_apis": self._check_external_apis_health(),
            "resources": self._check_system_resources(),
            "application": self._check_application_health(),
        }
        
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await asyncio.wait_for(task, timeout=10)
            except asyncio.TimeoutError:
                results[name] = ServiceStatus(
                    status="unhealthy",
                    response_time=10.0,
                    details={"error": "Health check timeout"}
                )
            except Exception as e:
                results[name] = ServiceStatus(
                    status="unhealthy", 
                    response_time=0,
                    details={"error": str(e)}
                )
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(results)
        
        health_report = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": self.config.VERSION,
            "uptime": str(datetime.utcnow() - self.startup_time),
            "services": {
                name: {
                    "status": result.status,
                    "response_time": f"{result.response_time:.2f}ms",
                    "details": result.details or {}
                }
                for name, result in results.items()
            }
        }
        
        # Cache result
        self._cache_result(cache_key, health_report)
        
        return health_report
    
    async def _check_redis_health(self) -> ServiceStatus:
        """Check Redis connectivity and performance."""
        
        start_time = time.time()
        try:
            # Test basic connectivity
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.ping
            )
            
            # Test write/read operations
            test_key = "health_check_test"
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.setex, test_key, 10, "test_value"
            )
            
            value = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.get, test_key
            )
            
            if value != b"test_value":
                raise ValueError("Redis read/write test failed")
            
            # Get Redis info
            info = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.info
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return ServiceStatus(
                status="healthy",
                response_time=response_time,
                details={
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "total_commands_processed": info.get("total_commands_processed")
                }
            )
        
        except Exception as e:
            return ServiceStatus(
                status="unhealthy",
                response_time=(time.time() - start_time) * 1000,
                details={"error": str(e)}
            )
    
    async def _check_external_apis_health(self) -> ServiceStatus:
        """Check external API connectivity and response times."""
        
        start_time = time.time()
        api_results = {}
        
        # Test Bright Data API
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    "https://api.brightdata.com/request",
                    headers={"Authorization": f"Bearer {self.config.BRIGHT_DATA_TOKEN}"},
                    params={"q": "test", "limit": 1}
                )
                
                api_results["bright_data"] = {
                    "status": "healthy" if response.status_code == 200 else "degraded",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() * 1000
                }
        
        except Exception as e:
            api_results["bright_data"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall API health
        healthy_apis = sum(1 for api in api_results.values() if api.get("status") == "healthy")
        total_apis = len(api_results)
        
        if healthy_apis == total_apis:
            status = "healthy"
        elif healthy_apis > 0:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return ServiceStatus(
            status=status,
            response_time=(time.time() - start_time) * 1000,
            details=api_results
        )
    
    async def _check_system_resources(self) -> ServiceStatus:
        """Check system resource utilization."""
        
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 95 or disk.percent > 95:
                status = "unhealthy"
            elif cpu_percent > 80 or memory.percent > 90 or disk.percent > 85:
                status = "degraded"
            else:
                status = "healthy"
            
            return ServiceStatus(
                status=status,
                response_time=(time.time() - start_time) * 1000,
                details={
                    "cpu_usage_percent": cpu_percent,
                    "memory_usage_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_usage_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            )
        
        except Exception as e:
            return ServiceStatus(
                status="unhealthy",
                response_time=(time.time() - start_time) * 1000,
                details={"error": str(e)}
            )
    
    async def _check_application_health(self) -> ServiceStatus:
        """Check application-specific health metrics."""
        
        start_time = time.time()
        
        try:
            # Get application metrics from Redis
            metrics = {}
            
            # Request rate (requests per minute)
            current_minute = int(time.time() // 60)
            request_count = self.redis.get(f"requests_per_minute:{current_minute}") or 0
            metrics["requests_per_minute"] = int(request_count)
            
            # Error rate (last hour)
            error_count = self.redis.get("errors_last_hour") or 0
            total_requests = self.redis.get("requests_last_hour") or 1
            error_rate = int(error_count) / int(total_requests) * 100
            metrics["error_rate_percent"] = round(error_rate, 2)
            
            # Cache hit rate
            cache_hits = self.redis.get("cache_hits") or 0
            cache_misses = self.redis.get("cache_misses") or 0
            total_cache_requests = int(cache_hits) + int(cache_misses)
            if total_cache_requests > 0:
                cache_hit_rate = int(cache_hits) / total_cache_requests * 100
                metrics["cache_hit_rate_percent"] = round(cache_hit_rate, 2)
            else:
                metrics["cache_hit_rate_percent"] = 0
            
            # Active connections
            active_connections = self.redis.get("active_connections") or 0
            metrics["active_connections"] = int(active_connections)
            
            # Determine application health
            if error_rate > 10 or metrics["requests_per_minute"] == 0:
                status = "unhealthy"
            elif error_rate > 5:
                status = "degraded"
            else:
                status = "healthy"
            
            return ServiceStatus(
                status=status,
                response_time=(time.time() - start_time) * 1000,
                details=metrics
            )
        
        except Exception as e:
            return ServiceStatus(
                status="unhealthy",
                response_time=(time.time() - start_time) * 1000,
                details={"error": str(e)}
            )
    
    def _calculate_overall_status(self, results: Dict[str, ServiceStatus]) -> str:
        """Calculate overall system status from individual service statuses."""
        
        statuses = [result.status for result in results.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"
    
    def _get_cached_result(self, cache_key: str) -> Dict[str, Any]:
        """Get cached health check result if still valid."""
        
        cached_data = self._cache.get(cache_key)
        if cached_data and time.time() - cached_data["timestamp"] < self._cache_ttl:
            return cached_data["result"]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache health check result."""
        
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "result": result
        }
```

## Metrics Collection

### Prometheus Metrics

#### Custom Metrics Implementation
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, multiprocess, generate_latest
import time
import os
from functools import wraps

# Create metrics registry
registry = CollectorRegistry()

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
    registry=registry
)

COMPANY_EXTRACTION_DURATION = Histogram(
    'company_extraction_duration_seconds',
    'Company extraction duration',
    ['extraction_mode', 'status'],
    buckets=(5.0, 10.0, 20.0, 30.0, 60.0, 120.0, 180.0, 300.0),
    registry=registry
)

CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Cache operations',
    ['operation', 'result'],
    registry=registry
)

EXTERNAL_API_CALLS = Counter(
    'external_api_calls_total',
    'External API calls',
    ['api', 'status'],
    registry=registry
)

EXTERNAL_API_DURATION = Histogram(
    'external_api_duration_seconds',
    'External API call duration',
    ['api'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry
)

ACTIVE_EXTRACTIONS = Gauge(
    'active_extractions',
    'Number of active company extractions',
    registry=registry
)

BATCH_QUEUE_SIZE = Gauge(
    'batch_queue_size',
    'Number of batches in queue',
    ['priority'],
    registry=registry
)

SYSTEM_INFO = Info(
    'system_info',
    'System information',
    registry=registry
)

# Metric decorators
def track_requests(func):
    """Decorator to track HTTP requests."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request') or args[0]
        method = request.method
        endpoint = request.url.path
        
        start_time = time.time()
        
        try:
            response = await func(*args, **kwargs)
            status_code = getattr(response, 'status_code', 200)
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            return response
            
        except Exception as e:
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            raise e
            
        finally:
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)
    
    return wrapper

def track_extraction(func):
    """Decorator to track company extractions."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        extraction_mode = kwargs.get('extraction_mode', 'standard')
        
        start_time = time.time()
        ACTIVE_EXTRACTIONS.inc()
        
        try:
            result = await func(*args, **kwargs)
            
            COMPANY_EXTRACTION_DURATION.labels(
                extraction_mode=extraction_mode,
                status='success'
            ).observe(time.time() - start_time)
            
            return result
            
        except Exception as e:
            COMPANY_EXTRACTION_DURATION.labels(
                extraction_mode=extraction_mode,
                status='error'
            ).observe(time.time() - start_time)
            raise e
            
        finally:
            ACTIVE_EXTRACTIONS.dec()
    
    return wrapper

def track_external_api(api_name: str):
    """Decorator to track external API calls."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                EXTERNAL_API_CALLS.labels(
                    api=api_name,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                EXTERNAL_API_CALLS.labels(
                    api=api_name,
                    status='error'
                ).inc()
                raise e
                
            finally:
                EXTERNAL_API_DURATION.labels(
                    api=api_name
                ).observe(time.time() - start_time)
        
        return wrapper
    return decorator

def track_cache_operation(operation: str, hit: bool = None):
    """Track cache operations."""
    
    if hit is not None:
        result = 'hit' if hit else 'miss'
    else:
        result = 'unknown'
    
    CACHE_OPERATIONS.labels(
        operation=operation,
        result=result
    ).inc()

# Initialize system info
def initialize_system_info():
    """Initialize system information metric."""
    
    SYSTEM_INFO.info({
        'version': os.getenv('VERSION', '1.0.0'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'python_version': os.getenv('PYTHON_VERSION', '3.11'),
        'hostname': os.getenv('HOSTNAME', 'localhost')
    })

# Metrics endpoint
async def get_metrics():
    """Generate Prometheus metrics."""
    
    if os.getenv('PROMETHEUS_MULTIPROC_DIR'):
        # Multi-process mode
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    
    return generate_latest(registry)

# Initialize metrics on import
initialize_system_info()
```

#### Business Metrics Tracking
```python
# business_metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Business-specific metrics
COMPANIES_EXTRACTED = Counter(
    'companies_extracted_total',
    'Total companies extracted successfully',
    ['industry', 'extraction_mode', 'source']
)

EXTRACTION_CONFIDENCE = Histogram(
    'extraction_confidence_score',
    'Confidence score of extractions',
    ['extraction_mode'],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0)
)

DATA_COMPLETENESS = Histogram(
    'extraction_data_completeness',
    'Percentage of extracted data fields that were populated',
    ['extraction_mode'],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0)
)

BATCH_PROCESSING_TIME = Histogram(
    'batch_processing_duration_seconds',
    'Time taken to process batches',
    ['batch_size_range'],
    buckets=(60, 300, 600, 1200, 1800, 3600, 7200)
)

USER_EXTRACTION_PATTERNS = Counter(
    'user_extraction_patterns_total',
    'User extraction patterns',
    ['user_id', 'extraction_mode', 'time_of_day']
)

def track_business_metrics(extraction_result: dict, extraction_mode: str):
    """Track business-specific metrics from extraction results."""
    
    # Track successful extraction
    COMPANIES_EXTRACTED.labels(
        industry=extraction_result.get('industry', 'unknown'),
        extraction_mode=extraction_mode,
        source='api'
    ).inc()
    
    # Track confidence score
    confidence = extraction_result.get('metadata', {}).get('confidence_score', 0)
    EXTRACTION_CONFIDENCE.labels(
        extraction_mode=extraction_mode
    ).observe(confidence)
    
    # Calculate and track data completeness
    expected_fields = get_expected_fields_for_mode(extraction_mode)
    populated_fields = count_populated_fields(extraction_result)
    completeness = populated_fields / len(expected_fields) if expected_fields else 0
    
    DATA_COMPLETENESS.labels(
        extraction_mode=extraction_mode
    ).observe(completeness)

def get_expected_fields_for_mode(extraction_mode: str) -> list:
    """Get list of expected fields for each extraction mode."""
    
    field_sets = {
        'basic': [
            'company_name', 'domain', 'industry', 'employee_count',
            'headquarters', 'contact_info'
        ],
        'standard': [
            'company_name', 'domain', 'industry', 'description', 'employee_count',
            'founded_year', 'headquarters', 'contact_info', 'financial_data',
            'social_media', 'key_personnel'
        ],
        'comprehensive': [
            'company_name', 'domain', 'industry', 'description', 'employee_count',
            'founded_year', 'company_type', 'headquarters', 'contact_info',
            'financial_data', 'social_media', 'key_personnel', 'products_services',
            'competitors', 'recent_news'
        ]
    }
    
    return field_sets.get(extraction_mode, field_sets['standard'])

def count_populated_fields(extraction_result: dict) -> int:
    """Count the number of populated fields in extraction result."""
    
    count = 0
    
    def is_populated(value):
        if value is None or value == '':
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True
    
    def count_nested(obj, prefix=''):
        nonlocal count
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_name = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)) and value:
                    count_nested(value, field_name)
                elif is_populated(value):
                    count += 1
        elif isinstance(obj, list) and obj:
            count += 1
    
    count_nested(extraction_result)
    return count
```

## Alerting System

### Alert Rules Configuration

#### Prometheus Alert Rules
```yaml
# alert_rules.yml
groups:
  - name: company-extraction-critical
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.instance }} has been down for more than 1 minute"
          runbook_url: "https://docs.company.com/runbooks/service-down"
      
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status_code=~"5.."}[5m]) /
          rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"
      
      - alert: ExtractionServiceOverloaded
        expr: active_extractions > 20
        for: 3m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Too many concurrent extractions"
          description: "{{ $value }} concurrent extractions are running"
      
      - alert: ExternalAPIFailure
        expr: |
          rate(external_api_calls_total{status="error"}[5m]) /
          rate(external_api_calls_total[5m]) > 0.20
        for: 3m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High external API failure rate"
          description: "{{ $labels.api }} API failure rate is {{ $value | humanizePercentage }}"

  - name: company-extraction-performance
    interval: 60s
    rules:
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 60
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "API response time is slow"
          description: "95th percentile response time is {{ $value }} seconds"
      
      - alert: LowCacheHitRate
        expr: |
          rate(cache_operations_total{result="hit"}[10m]) /
          rate(cache_operations_total[10m]) < 0.5
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Cache hit rate is low"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
      
      - alert: MemoryUsageHigh
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) /
          node_memory_MemTotal_bytes > 0.90
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

  - name: company-extraction-business
    interval: 300s  # Check every 5 minutes
    rules:
      - alert: LowExtractionSuccess
        expr: |
          rate(companies_extracted_total[1h]) /
          rate(http_requests_total{endpoint="/api/v1/company/extract"}[1h]) < 0.85
        for: 15m
        labels:
          severity: warning
          team: business
        annotations:
          summary: "Company extraction success rate is low"
          description: "Success rate is {{ $value | humanizePercentage }} over the last hour"
      
      - alert: NoExtractionsRecent
        expr: |
          rate(companies_extracted_total[30m]) == 0
        for: 30m
        labels:
          severity: warning
          team: business
        annotations:
          summary: "No successful extractions in the last 30 minutes"
          description: "The system hasn't performed any successful extractions recently"
```

#### Alert Manager Configuration
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'alerts@company.com'
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'team']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 10s
      repeat_interval: 5m
    
    - match:
        team: business
      receiver: 'business-alerts'
      group_interval: 30m
      repeat_interval: 4h

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts-general'
        title: 'Company Extraction API Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        title: 'CRITICAL: Company Extraction API'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
        color: 'danger'
    email_configs:
      - to: 'oncall@company.com'
        subject: 'CRITICAL: Company Extraction API Alert'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          Runbook: {{ .Annotations.runbook_url }}
          {{ end }}
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        
  - name: 'business-alerts'
    slack_configs:
      - channel: '#business-metrics'
        title: 'Business Metric Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        color: 'warning'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### Custom Alert Handlers

#### Intelligent Alert Processor
```python
# alert_processor.py
import asyncio
import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

@dataclass
class Alert:
    name: str
    severity: str
    status: str
    starts_at: datetime
    ends_at: datetime = None
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None

class AlertProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("alerting")
        self.alert_history = []
        self.notification_channels = {
            "slack": self._send_slack_notification,
            "email": self._send_email_notification,
            "pagerduty": self._send_pagerduty_notification,
            "webhook": self._send_webhook_notification
        }
    
    async def process_webhook_alerts(self, alert_data: Dict[str, Any]):
        """Process incoming webhook alerts from Prometheus AlertManager."""
        
        alerts = []
        for alert_dict in alert_data.get('alerts', []):
            alert = Alert(
                name=alert_dict['labels']['alertname'],
                severity=alert_dict['labels'].get('severity', 'info'),
                status=alert_dict['status'],
                starts_at=datetime.fromisoformat(
                    alert_dict['startsAt'].replace('Z', '+00:00')
                ),
                ends_at=datetime.fromisoformat(
                    alert_dict['endsAt'].replace('Z', '+00:00')
                ) if alert_dict.get('endsAt') else None,
                labels=alert_dict.get('labels', {}),
                annotations=alert_dict.get('annotations', {})
            )
            alerts.append(alert)
        
        # Process each alert
        for alert in alerts:
            await self._process_single_alert(alert)
    
    async def _process_single_alert(self, alert: Alert):
        """Process a single alert with intelligent routing."""
        
        # Add to history
        self.alert_history.append(alert)
        
        # Keep only recent alerts (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.alert_history = [
            a for a in self.alert_history 
            if a.starts_at > cutoff_time
        ]
        
        # Check for alert flapping
        if self._is_alert_flapping(alert):
            await self._handle_flapping_alert(alert)
            return
        
        # Route alert based on severity and type
        routing_config = self._get_alert_routing(alert)
        
        # Send notifications
        for channel, config in routing_config.items():
            try:
                await self.notification_channels[channel](alert, config)
            except Exception as e:
                self.logger.error(f"Failed to send {channel} notification: {e}")
        
        # Handle special alert types
        await self._handle_special_alerts(alert)
    
    def _is_alert_flapping(self, alert: Alert, window_minutes: int = 30) -> bool:
        """Check if an alert is flapping (firing and resolving repeatedly)."""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_same_alerts = [
            a for a in self.alert_history
            if a.name == alert.name and a.starts_at > cutoff_time
        ]
        
        # Consider flapping if more than 5 occurrences in the window
        return len(recent_same_alerts) > 5
    
    async def _handle_flapping_alert(self, alert: Alert):
        """Handle flapping alerts by grouping notifications."""
        
        flapping_message = {
            "type": "flapping_alert",
            "alert_name": alert.name,
            "occurrences": len([
                a for a in self.alert_history[-10:] 
                if a.name == alert.name
            ]),
            "message": f"Alert {alert.name} is flapping. Grouping notifications."
        }
        
        # Send flapping notification to ops channel
        await self._send_slack_notification(
            alert, 
            {"channel": "#ops-alerts", "message": flapping_message}
        )
        
        self.logger.warning(f"Alert flapping detected: {alert.name}")
    
    def _get_alert_routing(self, alert: Alert) -> Dict[str, Dict]:
        """Get notification routing configuration for an alert."""
        
        routing = {}
        
        # Base routing by severity
        if alert.severity == "critical":
            routing["slack"] = {"channel": "#alerts-critical"}
            routing["pagerduty"] = {"service_key": self.config.PAGERDUTY_SERVICE_KEY}
            routing["email"] = {"recipients": ["oncall@company.com"]}
            
        elif alert.severity == "warning":
            routing["slack"] = {"channel": "#alerts-warning"}
            
        else:  # info
            routing["slack"] = {"channel": "#alerts-info"}
        
        # Special routing for business alerts
        if alert.labels.get("team") == "business":
            routing["slack"] = {"channel": "#business-metrics"}
        
        # Time-based routing (quiet hours)
        current_hour = datetime.utcnow().hour
        if current_hour < 8 or current_hour > 22:  # Outside business hours
            if alert.severity != "critical":
                # Reduce notifications during quiet hours
                routing.pop("email", None)
                routing.pop("pagerduty", None)
        
        return routing
    
    async def _send_slack_notification(self, alert: Alert, config: Dict):
        """Send Slack notification."""
        
        color = {
            "critical": "danger",
            "warning": "warning", 
            "info": "good"
        }.get(alert.severity, "good")
        
        message = {
            "channel": config["channel"],
            "attachments": [{
                "color": color,
                "title": f"{alert.severity.upper()}: {alert.name}",
                "text": alert.annotations.get("summary", "No summary available"),
                "fields": [
                    {
                        "title": "Description",
                        "value": alert.annotations.get("description", "N/A"),
                        "short": False
                    },
                    {
                        "title": "Status",
                        "value": alert.status,
                        "short": True
                    },
                    {
                        "title": "Started At",
                        "value": alert.starts_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "short": True
                    }
                ],
                "footer": "Company Extraction API Monitoring",
                "ts": alert.starts_at.timestamp()
            }]
        }
        
        # Add runbook link if available
        if alert.annotations.get("runbook_url"):
            message["attachments"][0]["actions"] = [{
                "type": "button",
                "text": "Runbook",
                "url": alert.annotations["runbook_url"]
            }]
        
        async with httpx.AsyncClient() as client:
            await client.post(
                self.config.SLACK_WEBHOOK_URL,
                json=message
            )
    
    async def _handle_special_alerts(self, alert: Alert):
        """Handle special alert types with automated responses."""
        
        # Auto-scaling for high load
        if alert.name == "ExtractionServiceOverloaded":
            await self._trigger_auto_scaling()
        
        # Cache warming for low hit rates
        elif alert.name == "LowCacheHitRate":
            await self._trigger_cache_warming()
        
        # Circuit breaker for external API failures
        elif alert.name == "ExternalAPIFailure":
            await self._trigger_circuit_breaker(alert.labels.get("api"))
    
    async def _trigger_auto_scaling(self):
        """Trigger auto-scaling for high load conditions."""
        
        self.logger.info("Triggering auto-scaling due to high load")
        
        # Example: Scale up Docker containers
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.ORCHESTRATOR_URL}/scale",
                    json={"service": "company-extraction-api", "replicas": 5}
                )
        except Exception as e:
            self.logger.error(f"Failed to trigger auto-scaling: {e}")
    
    async def _trigger_cache_warming(self):
        """Trigger cache warming for popular companies."""
        
        self.logger.info("Triggering cache warming due to low hit rate")
        
        # Get list of popular companies to pre-warm
        popular_companies = [
            "Apple", "Microsoft", "Google", "Amazon", "Tesla"
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.API_BASE_URL}/internal/cache/warm",
                    json={"companies": popular_companies}
                )
        except Exception as e:
            self.logger.error(f"Failed to trigger cache warming: {e}")
```

## Dashboard Configuration

### Grafana Dashboard Setup

#### System Overview Dashboard
```json
{
  "dashboard": {
    "id": null,
    "title": "Company Extraction API - System Overview",
    "tags": ["company-extraction", "overview"],
    "timezone": "UTC",
    "refresh": "30s",
    "panels": [
      {
        "title": "System Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"company-extraction-api\"}",
            "legendFormat": "Service Status"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {"options": {"0": {"text": "DOWN", "color": "red"}}}
            ]
          }
        }
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          },
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))", 
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      },
      {
        "title": "Active Extractions",
        "type": "stat",
        "targets": [
          {
            "expr": "active_extractions",
            "legendFormat": "Active"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(cache_operations_total{result=\"hit\"}[5m]) / rate(cache_operations_total[5m])",
            "legendFormat": "Hit Rate"
          }
        ]
      }
    ]
  }
}
```

## Log Management

### Structured Logging Setup

#### Log Aggregation with ELK Stack
```yaml
# logstash.conf
input {
  beats {
    port => 5044
  }
  
  http {
    port => 8080
    codec => json
  }
}

filter {
  if [fields][service] == "company-extraction-api" {
    # Parse JSON log format
    json {
      source => "message"
    }
    
    # Add parsed fields
    mutate {
      add_field => { "service_name" => "company-extraction-api" }
    }
    
    # Parse timestamp
    date {
      match => [ "timestamp", "ISO8601" ]
    }
    
    # Extract trace ID for correlation
    if [trace_id] {
      mutate {
        add_field => { "correlation_id" => "%{trace_id}" }
      }
    }
    
    # Categorize log levels
    if [level] == "ERROR" or [level] == "CRITICAL" {
      mutate {
        add_tag => ["error"]
      }
    }
    
    if [level] == "WARNING" {
      mutate {
        add_tag => ["warning"]
      }
    }
    
    # Extract business metrics
    if [message] =~ /Company extraction completed/ {
      grok {
        match => { 
          "message" => "Company extraction completed for %{WORD:company_name} in %{NUMBER:extraction_time:float}s with confidence %{NUMBER:confidence_score:float}"
        }
      }
      
      mutate {
        add_tag => ["business_metric", "extraction_completed"]
      }
    }
    
    if [message] =~ /External API call/ {
      grok {
        match => {
          "message" => "External API call to %{WORD:api_name} took %{NUMBER:api_response_time:float}s with status %{NUMBER:api_status_code:int}"
        }
      }
      
      mutate {
        add_tag => ["external_api", "performance"]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "company-extraction-api-%{+YYYY.MM.dd}"
  }
  
  # Send errors to separate index
  if "error" in [tags] {
    elasticsearch {
      hosts => ["elasticsearch:9200"]
      index => "company-extraction-errors-%{+YYYY.MM.dd}"
    }
  }
  
  # Send business metrics to separate index
  if "business_metric" in [tags] {
    elasticsearch {
      hosts => ["elasticsearch:9200"]
      index => "company-extraction-business-%{+YYYY.MM.dd}"
    }
  }
  
  stdout { codec => rubydebug }
}
```

#### Log Analysis Queries

**Common Kibana Queries:**

1. **Error Analysis:**
   ```lucene
   level:ERROR AND timestamp:[now-1h TO now]
   ```

2. **Performance Issues:**
   ```lucene
   extraction_time:>60 AND timestamp:[now-24h TO now]
   ```

3. **API Success Rate:**
   ```lucene
   tags:external_api AND api_status_code:[200 TO 299]
   ```

4. **Business Intelligence:**
   ```lucene
   tags:extraction_completed AND confidence_score:>0.9
   ```

## Best Practices

### Monitoring Best Practices

1. **Golden Signals**: Focus on latency, traffic, errors, and saturation
2. **SLA Monitoring**: Track service level agreements and objectives
3. **Alerting Hygiene**: Regularly review and tune alert thresholds
4. **Dashboard Clarity**: Create clear, actionable dashboards
5. **On-call Readiness**: Ensure alerts are actionable and include runbooks

### Performance Monitoring

1. **Baseline Establishment**: Establish performance baselines
2. **Trend Analysis**: Monitor long-term trends and patterns
3. **Capacity Planning**: Proactive capacity planning based on growth
4. **Resource Optimization**: Regular review of resource utilization
5. **Cost Monitoring**: Track infrastructure and operational costs

### Log Management

1. **Structured Logging**: Use consistent, structured log formats
2. **Log Levels**: Appropriate use of log levels (DEBUG, INFO, WARN, ERROR)
3. **Sensitive Data**: Never log sensitive information
4. **Retention Policies**: Implement appropriate log retention policies
5. **Performance Impact**: Monitor logging performance impact

## Next Steps

1. **Deploy Monitoring**: Set up Prometheus, Grafana, and AlertManager
2. **Configure Alerts**: Create and tune alert rules
3. **Set Up Dashboards**: Create operational and business dashboards
4. **Test Alerting**: Verify alert routing and notification channels
5. **Create Runbooks**: Document response procedures for common alerts
6. **Train Team**: Ensure team familiarity with monitoring tools and procedures

## Related Documentation

- [Operations Guide](./README.md) - Main operations documentation
- [Security Guide](./security.md) - Security monitoring and procedures  
- [Troubleshooting Guide](./troubleshooting.md) - Issue resolution procedures
- [Performance Guide](../user/performance-guide.md) - Performance optimization