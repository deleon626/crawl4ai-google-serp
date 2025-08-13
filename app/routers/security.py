"""
Security management and monitoring endpoints.

This module provides endpoints for security monitoring, compliance reporting,
and system health checks for enterprise deployments.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.security.rate_limiting import rate_limiter
from app.security.security import security_manager
from app.compliance.monitoring import compliance_manager
from app.monitoring.production import production_monitor

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class SecurityStatus(BaseModel):
    """Security system status response."""
    
    status: str = Field(description="Overall security status")
    timestamp: datetime = Field(description="Status check timestamp")
    components: Dict = Field(description="Individual component statuses")
    threats_detected: int = Field(description="Number of active threats")
    alerts_active: int = Field(description="Number of active alerts")
    compliance_status: str = Field(description="Compliance status")


class ComplianceReport(BaseModel):
    """GDPR compliance report."""
    
    report_type: str = Field(description="Type of compliance report")
    generated_at: datetime = Field(description="Report generation timestamp")
    data_subjects_count: int = Field(description="Number of data subjects")
    records_count: int = Field(description="Number of data records")
    violations_count: int = Field(description="Number of compliance violations")
    audit_entries_count: int = Field(description="Number of audit log entries")
    retention_stats: Dict = Field(description="Data retention statistics")
    overall_compliance: str = Field(description="Overall compliance assessment")


class SecurityMetrics(BaseModel):
    """Security metrics and statistics."""
    
    period: str = Field(description="Metrics period")
    rate_limit_violations: int = Field(description="Rate limit violations")
    security_violations: int = Field(description="Security violations")
    blocked_requests: int = Field(description="Blocked requests")
    suspicious_activity: int = Field(description="Suspicious activity incidents")
    avg_response_time_ms: float = Field(description="Average response time")
    error_rate_percent: float = Field(description="Error rate percentage")


async def verify_admin_access(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify admin access for security endpoints."""
    # In production, implement proper JWT token verification
    # For now, accept any bearer token for demo purposes
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # TODO: Implement proper token verification
    return True


@router.get("/status", 
            response_model=SecurityStatus,
            summary="Get overall security system status",
            description="Returns comprehensive security status including all monitoring components")
async def get_security_status(admin: bool = Depends(verify_admin_access)) -> SecurityStatus:
    """Get comprehensive security system status."""
    try:
        # Get system health from production monitor
        system_health = production_monitor.get_system_health()
        
        # Get compliance report
        compliance_report = compliance_manager.get_compliance_report()
        
        # Get rate limiting stats
        rate_limit_stats = {
            "blocked_domains": len(rate_limiter.abuse_detector.client_patterns),
            "violations_count": len(rate_limiter.security_events)
        }
        
        # Get security violations
        security_violations = len(security_manager.get_violations(limit=1000))
        
        # Count active alerts
        active_alerts = len([a for a in production_monitor.get_alerts(limit=1000) if not a.resolved])
        
        return SecurityStatus(
            status=system_health["overall_status"],
            timestamp=datetime.utcnow(),
            components={
                "rate_limiting": "active" if rate_limiter else "inactive",
                "security_validation": "active" if security_manager else "inactive",
                "compliance_monitoring": "active" if compliance_manager else "inactive",
                "production_monitoring": "active" if production_monitor else "inactive",
                "system_health": system_health
            },
            threats_detected=security_violations,
            alerts_active=active_alerts,
            compliance_status=compliance_report.get("compliance_status", "unknown")
        )
    
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security status: {str(e)}"
        )


@router.get("/compliance/report",
            response_model=ComplianceReport,
            summary="Get GDPR compliance report",
            description="Returns detailed GDPR compliance report with statistics and violations")
async def get_compliance_report(admin: bool = Depends(verify_admin_access)) -> ComplianceReport:
    """Get comprehensive GDPR compliance report."""
    try:
        report_data = compliance_manager.get_compliance_report()
        
        return ComplianceReport(
            report_type="gdpr_compliance",
            generated_at=datetime.fromisoformat(report_data["report_generated_at"]),
            data_subjects_count=report_data["data_subjects"]["total"],
            records_count=report_data["data_records"]["total"],
            violations_count=report_data["violations"]["total"],
            audit_entries_count=report_data["audit_log_entries"],
            retention_stats=report_data["data_records"],
            overall_compliance=report_data["compliance_status"]
        )
    
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.get("/metrics",
            response_model=SecurityMetrics,
            summary="Get security metrics",
            description="Returns security metrics and performance statistics")
async def get_security_metrics(
    period: str = Query("1h", description="Metrics period (1h, 24h, 7d)"),
    admin: bool = Depends(verify_admin_access)
) -> SecurityMetrics:
    """Get security metrics for specified period."""
    try:
        # Get rate limiting violations
        rate_limit_events = rate_limiter.get_security_events(limit=10000)
        rate_limit_violations = len(rate_limit_events)
        
        # Get security violations
        security_violations = security_manager.get_violations(limit=10000)
        security_violation_count = len(security_violations)
        
        # Get blocked requests count
        blocked_requests = len([e for e in rate_limit_events if "blocked" in e.action_taken])
        
        # Get suspicious activity
        suspicious_patterns = sum(1 for pattern in rate_limiter.abuse_detector.client_patterns.values()
                                if pattern.suspicious_score > 0.7)
        
        # Get response time metrics
        response_times = production_monitor.get_metrics("request_response_time", limit=1000)
        avg_response_time = sum(m.value for m in response_times) / len(response_times) if response_times else 0.0
        
        # Get error rate
        error_metrics = production_monitor.get_metrics("request_error_count", limit=1000)
        total_requests = production_monitor.get_metrics("request_count", limit=1000)
        error_rate = (len(error_metrics) / max(len(total_requests), 1)) * 100
        
        return SecurityMetrics(
            period=period,
            rate_limit_violations=rate_limit_violations,
            security_violations=security_violation_count,
            blocked_requests=blocked_requests,
            suspicious_activity=suspicious_patterns,
            avg_response_time_ms=avg_response_time,
            error_rate_percent=error_rate
        )
    
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security metrics: {str(e)}"
        )


@router.get("/alerts",
            summary="Get security alerts",
            description="Returns recent security alerts and notifications")
async def get_security_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (info, warning, error, critical)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts to return"),
    admin: bool = Depends(verify_admin_access)
) -> Dict:
    """Get recent security alerts."""
    try:
        # Get alerts from production monitor
        severity_filter = production_monitor.AlertSeverity(severity) if severity else None
        alerts = production_monitor.get_alerts(severity=severity_filter, limit=limit)
        
        # Get rate limiting events
        rate_limit_events = rate_limiter.get_security_events(limit=limit)
        
        # Get security violations
        security_violations = security_manager.get_violations(limit=limit, severity=severity)
        
        return {
            "alerts": [alert.dict() for alert in alerts],
            "rate_limit_events": [event.dict() for event in rate_limit_events],
            "security_violations": [violation.dict() for violation in security_violations],
            "total_count": len(alerts) + len(rate_limit_events) + len(security_violations),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get security alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security alerts: {str(e)}"
        )


@router.post("/compliance/data_subject_request",
             summary="Process data subject rights request",
             description="Process GDPR data subject rights requests (access, portability, erasure, etc.)")
async def process_data_subject_request(
    subject_id: str,
    request_type: str,
    details: Optional[Dict] = None,
    admin: bool = Depends(verify_admin_access)
) -> Dict:
    """Process data subject rights request under GDPR."""
    try:
        result = await compliance_manager.process_data_subject_request(
            subject_id=subject_id,
            request_type=request_type,
            details=details or {}
        )
        
        return {
            "success": True,
            "request_id": f"dsr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to process data subject request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process data subject request: {str(e)}"
        )


@router.post("/maintenance/cleanup",
             summary="Run maintenance cleanup",
             description="Run maintenance tasks including retention cleanup and data archival")
async def run_maintenance_cleanup(admin: bool = Depends(verify_admin_access)) -> Dict:
    """Run maintenance cleanup tasks."""
    try:
        # Run retention cleanup
        cleanup_stats = await compliance_manager.run_retention_cleanup()
        
        # Cleanup old monitoring data
        production_monitor.cleanup()
        rate_limiter.cleanup()
        
        return {
            "success": True,
            "cleanup_stats": cleanup_stats,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Maintenance cleanup completed successfully"
        }
    
    except Exception as e:
        logger.error(f"Failed to run maintenance cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run maintenance cleanup: {str(e)}"
        )


@router.get("/health/components",
            summary="Get detailed component health",
            description="Returns health status for all system components")
async def get_component_health(admin: bool = Depends(verify_admin_access)) -> Dict:
    """Get detailed health status for all components."""
    try:
        # Register health checks for all components
        health_results = {}
        
        # Rate limiter health
        health_results["rate_limiter"] = await production_monitor.register_health_check(
            "rate_limiter",
            lambda: {"status": "healthy" if rate_limiter else "unhealthy"}
        )
        
        # Security manager health
        health_results["security_manager"] = await production_monitor.register_health_check(
            "security_manager", 
            lambda: {"status": "healthy" if security_manager else "unhealthy"}
        )
        
        # Compliance manager health
        health_results["compliance_manager"] = await production_monitor.register_health_check(
            "compliance_manager",
            lambda: {"status": "healthy" if compliance_manager else "unhealthy"}
        )
        
        # Production monitor health
        health_results["production_monitor"] = await production_monitor.register_health_check(
            "production_monitor",
            lambda: {"status": "healthy"}
        )
        
        return {
            "components": {name: check.dict() for name, check in health_results.items()},
            "overall_status": production_monitor.get_system_health()["overall_status"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get component health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve component health: {str(e)}"
        )