"""Monitoring and logging utilities for company extraction."""

import json
import logging
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import wraps

from app.utils.exceptions import generate_trace_id

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for tracking operation performance."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    trace_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        if self.duration is not None:
            data['duration'] = self.duration
        return data


class StructuredLogger:
    """Structured logger for enhanced monitoring."""
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.default_context = {}
    
    def set_context(self, **kwargs):
        """Set default context for all log messages."""
        self.default_context.update(kwargs)
    
    def log_operation_start(self, operation_name: str, **context) -> OperationMetrics:
        """Log operation start and return metrics tracker."""
        trace_id = generate_trace_id()
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            trace_id=trace_id,
            context={**self.default_context, **context}
        )
        
        self.logger.info(
            f"Operation started: {operation_name}",
            extra={
                "trace_id": trace_id,
                "operation": operation_name,
                "event_type": "operation_start",
                **context
            }
        )
        
        return metrics
    
    def log_operation_success(self, metrics: OperationMetrics, **additional_context):
        """Log successful operation completion."""
        metrics.end_time = time.time()
        metrics.success = True
        
        context = {**metrics.context, **additional_context} if metrics.context else additional_context
        
        self.logger.info(
            f"Operation completed successfully: {metrics.operation_name} "
            f"(duration: {metrics.duration:.2f}s)",
            extra={
                "trace_id": metrics.trace_id,
                "operation": metrics.operation_name,
                "duration": metrics.duration,
                "success": True,
                "event_type": "operation_success",
                **context
            }
        )
    
    def log_operation_error(self, metrics: OperationMetrics, error: Exception, **additional_context):
        """Log operation error."""
        metrics.end_time = time.time()
        metrics.success = False
        metrics.error_type = type(error).__name__
        metrics.error_message = str(error)
        
        context = {**metrics.context, **additional_context} if metrics.context else additional_context
        
        self.logger.error(
            f"Operation failed: {metrics.operation_name} "
            f"(duration: {metrics.duration:.2f}s, error: {metrics.error_type})",
            extra={
                "trace_id": metrics.trace_id,
                "operation": metrics.operation_name,
                "duration": metrics.duration,
                "success": False,
                "error_type": metrics.error_type,
                "error_message": metrics.error_message,
                "event_type": "operation_error",
                **context
            },
            exc_info=True
        )
    
    def log_business_event(self, event_type: str, message: str, **context):
        """Log business-relevant events."""
        self.logger.info(
            message,
            extra={
                "trace_id": generate_trace_id(),
                "event_type": event_type,
                "business_event": True,
                **self.default_context,
                **context
            }
        )
    
    def log_performance_metric(self, metric_name: str, value: Union[float, int], **context):
        """Log performance metrics."""
        self.logger.info(
            f"Performance metric - {metric_name}: {value}",
            extra={
                "trace_id": generate_trace_id(),
                "event_type": "performance_metric",
                "metric_name": metric_name,
                "metric_value": value,
                **self.default_context,
                **context
            }
        )


class ErrorTracker:
    """Track and analyze error patterns."""
    
    def __init__(self):
        """Initialize error tracker."""
        self.error_counts = {}
        self.error_rates = {}
    
    def record_error(self, error_type: str, operation: str, details: Dict[str, Any] = None):
        """Record an error occurrence."""
        timestamp = time.time()
        
        # Update error counts
        key = f"{operation}:{error_type}"
        if key not in self.error_counts:
            self.error_counts[key] = []
        
        self.error_counts[key].append({
            "timestamp": timestamp,
            "details": details or {}
        })
        
        # Clean old entries (keep last 24 hours)
        cutoff = timestamp - 86400  # 24 hours
        self.error_counts[key] = [
            entry for entry in self.error_counts[key]
            if entry["timestamp"] > cutoff
        ]
    
    def get_error_rate(self, operation: str, error_type: str, window_minutes: int = 60) -> float:
        """Calculate error rate for specific operation and error type."""
        key = f"{operation}:{error_type}"
        if key not in self.error_counts:
            return 0.0
        
        cutoff = time.time() - (window_minutes * 60)
        recent_errors = [
            entry for entry in self.error_counts[key]
            if entry["timestamp"] > cutoff
        ]
        
        return len(recent_errors) / window_minutes  # Errors per minute
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top error types by frequency."""
        error_summary = []
        
        for key, entries in self.error_counts.items():
            operation, error_type = key.split(":", 1)
            error_summary.append({
                "operation": operation,
                "error_type": error_type,
                "count": len(entries),
                "recent_count": len([e for e in entries if e["timestamp"] > time.time() - 3600]),
                "last_occurrence": max(e["timestamp"] for e in entries) if entries else None
            })
        
        return sorted(error_summary, key=lambda x: x["count"], reverse=True)[:limit]


class CompanyExtractionMonitor:
    """Specialized monitor for company extraction operations."""
    
    def __init__(self):
        """Initialize extraction monitor."""
        self.logger = StructuredLogger("company_extraction")
        self.error_tracker = ErrorTracker()
        self.extraction_stats = {
            "total_requests": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "avg_processing_time": 0.0,
            "avg_confidence_score": 0.0,
            "companies_processed": set()
        }
    
    def log_extraction_request(self, company_name: str, extraction_mode: str, **context) -> OperationMetrics:
        """Log start of company extraction."""
        self.extraction_stats["total_requests"] += 1
        
        return self.logger.log_operation_start(
            "company_extraction",
            company_name=company_name,
            extraction_mode=extraction_mode,
            **context
        )
    
    def log_extraction_success(self, metrics: OperationMetrics, 
                              company_name: str, confidence_score: float,
                              pages_crawled: int, sources_found: int, **context):
        """Log successful company extraction."""
        self.extraction_stats["successful_extractions"] += 1
        self.extraction_stats["companies_processed"].add(company_name.lower())
        
        # Update averages
        total_successful = self.extraction_stats["successful_extractions"]
        current_avg_time = self.extraction_stats["avg_processing_time"]
        current_avg_confidence = self.extraction_stats["avg_confidence_score"]
        
        self.extraction_stats["avg_processing_time"] = (
            (current_avg_time * (total_successful - 1) + metrics.duration) / total_successful
        )
        self.extraction_stats["avg_confidence_score"] = (
            (current_avg_confidence * (total_successful - 1) + confidence_score) / total_successful
        )
        
        self.logger.log_operation_success(
            metrics,
            company_name=company_name,
            confidence_score=confidence_score,
            pages_crawled=pages_crawled,
            sources_found=sources_found,
            **context
        )
        
        # Log business event
        self.logger.log_business_event(
            "company_extracted",
            f"Successfully extracted information for {company_name}",
            company_name=company_name,
            confidence_score=confidence_score,
            data_sources=sources_found
        )
    
    def log_extraction_failure(self, metrics: OperationMetrics, error: Exception,
                              company_name: str, **context):
        """Log failed company extraction."""
        self.extraction_stats["failed_extractions"] += 1
        
        error_type = type(error).__name__
        self.error_tracker.record_error(
            error_type, 
            "company_extraction",
            {"company_name": company_name, **context}
        )
        
        self.logger.log_operation_error(
            metrics,
            error,
            company_name=company_name,
            **context
        )
    
    def log_quality_assessment(self, company_name: str, quality_score: float, 
                              completeness_score: float, issues: List[str]):
        """Log data quality assessment."""
        self.logger.log_performance_metric(
            "data_quality_score",
            quality_score,
            company_name=company_name,
            completeness_score=completeness_score,
            quality_issues=issues
        )
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get current extraction statistics."""
        total_requests = self.extraction_stats["total_requests"]
        success_rate = (
            self.extraction_stats["successful_extractions"] / total_requests
            if total_requests > 0 else 0.0
        )
        
        return {
            **self.extraction_stats,
            "unique_companies_processed": len(self.extraction_stats["companies_processed"]),
            "success_rate": round(success_rate, 3),
            "failure_rate": round(1.0 - success_rate, 3),
            "top_errors": self.error_tracker.get_top_errors(5)
        }


# Global monitor instance
extraction_monitor = CompanyExtractionMonitor()


def monitor_extraction_operation(func):
    """Decorator to automatically monitor extraction operations."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract company name from arguments
        company_name = "unknown"
        extraction_mode = "unknown"
        
        if args and hasattr(args[0], 'company_name'):
            company_name = args[0].company_name
        if args and hasattr(args[0], 'extraction_mode'):
            extraction_mode = str(args[0].extraction_mode)
        
        # Start monitoring
        metrics = extraction_monitor.log_extraction_request(
            company_name, extraction_mode
        )
        
        try:
            result = await func(*args, **kwargs)
            
            # Extract success metrics from result
            confidence_score = 0.0
            pages_crawled = 0
            sources_found = 0
            
            if hasattr(result, 'company_information') and result.company_information:
                confidence_score = getattr(result.company_information, 'confidence_score', 0.0)
            if hasattr(result, 'extraction_metadata'):
                pages_crawled = getattr(result.extraction_metadata, 'pages_crawled', 0)
                sources_found = len(getattr(result.extraction_metadata, 'sources_found', []))
            
            extraction_monitor.log_extraction_success(
                metrics, company_name, confidence_score, pages_crawled, sources_found
            )
            
            return result
            
        except Exception as e:
            extraction_monitor.log_extraction_failure(metrics, e, company_name)
            raise
    
    return wrapper


def log_data_quality_assessment(company_name: str, assessment: Dict[str, Any]):
    """Log data quality assessment results."""
    extraction_monitor.log_quality_assessment(
        company_name,
        assessment.get("quality_score", 0.0),
        assessment.get("completeness_score", 0.0),
        assessment.get("issues", [])
    )


def get_monitoring_dashboard() -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data."""
    return {
        "extraction_stats": extraction_monitor.get_extraction_stats(),
        "system_health": {
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time(),  # This would be actual uptime in production
            "status": "operational"
        },
        "performance_metrics": {
            "avg_processing_time": extraction_monitor.extraction_stats["avg_processing_time"],
            "avg_confidence_score": extraction_monitor.extraction_stats["avg_confidence_score"]
        }
    }