"""
Compliance monitoring and audit trail system.

This module implements GDPR compliance, data retention policies,
audit trail generation, privacy enforcement, and terms of service compliance.
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

import aioredis
from fastapi import Request
from pydantic import BaseModel, Field, validator

from config.settings import settings

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """Categories of data for GDPR compliance."""
    PERSONAL_IDENTIFIABLE = "personal_identifiable"
    TECHNICAL_LOGS = "technical_logs"
    BUSINESS_DATA = "business_data"
    ANALYTICS_DATA = "analytics_data"
    SECURITY_LOGS = "security_logs"
    PERFORMANCE_METRICS = "performance_metrics"


class ProcessingLawfulBasis(str, Enum):
    """GDPR lawful basis for processing."""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataAction(str, Enum):
    """Types of data actions for audit trail."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"
    ANONYMIZE = "anonymize"
    ARCHIVE = "archive"


class ComplianceStatus(str, Enum):
    """Compliance status levels."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"


class DataSubject(BaseModel):
    """Data subject information for GDPR compliance."""
    
    subject_id: str = Field(description="Unique identifier for data subject")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    consent_given: bool = Field(default=False, description="Whether consent was given")
    consent_timestamp: Optional[datetime] = Field(default=None, description="When consent was given")
    consent_withdrawn: Optional[datetime] = Field(default=None, description="When consent was withdrawn")
    preferences: Dict = Field(default_factory=dict, description="Data processing preferences")
    opt_out_requests: List[str] = Field(default_factory=list, description="Opt-out requests made")


class DataRecord(BaseModel):
    """Individual data record with metadata."""
    
    record_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique record ID")
    subject_id: str = Field(description="Data subject identifier")
    data_category: DataCategory = Field(description="Category of data")
    lawful_basis: ProcessingLawfulBasis = Field(description="Legal basis for processing")
    purpose: str = Field(description="Purpose of data processing")
    data_content: Dict = Field(description="Actual data content")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    retention_period_days: int = Field(description="Retention period in days")
    is_sensitive: bool = Field(default=False, description="Whether data is sensitive")
    encryption_key_id: Optional[str] = Field(default=None, description="Encryption key identifier")
    access_log: List[str] = Field(default_factory=list, description="Access log entries")
    
    @validator('expires_at', always=True)
    def set_expiration(cls, v, values):
        if v is None and 'retention_period_days' in values and 'created_at' in values:
            return values['created_at'] + timedelta(days=values['retention_period_days'])
        return v


class AuditLogEntry(BaseModel):
    """Audit log entry for compliance tracking."""
    
    entry_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique entry ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Action timestamp")
    action: DataAction = Field(description="Action performed")
    subject_id: str = Field(description="Data subject identifier")
    record_id: Optional[str] = Field(default=None, description="Data record identifier")
    operator_id: str = Field(description="Who performed the action")
    ip_address: str = Field(description="IP address of operator")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    endpoint: str = Field(description="API endpoint used")
    request_method: str = Field(description="HTTP method")
    data_category: DataCategory = Field(description="Category of data affected")
    purpose: str = Field(description="Purpose of the action")
    lawful_basis: ProcessingLawfulBasis = Field(description="Legal basis")
    details: Dict = Field(default_factory=dict, description="Additional details")
    compliance_status: ComplianceStatus = Field(description="Compliance status of action")
    retention_applied: bool = Field(default=False, description="Whether retention policy was applied")
    hash_signature: Optional[str] = Field(default=None, description="Hash for integrity verification")
    
    def __post_init__(self):
        """Generate hash signature for integrity."""
        if not self.hash_signature:
            content = f"{self.timestamp}{self.action}{self.subject_id}{self.operator_id}{self.endpoint}"
            self.hash_signature = hashlib.sha256(content.encode()).hexdigest()


class ComplianceViolation(BaseModel):
    """Compliance violation record."""
    
    violation_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique violation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Violation timestamp")
    violation_type: str = Field(description="Type of compliance violation")
    severity: str = Field(description="Violation severity: low, medium, high, critical")
    subject_id: Optional[str] = Field(default=None, description="Affected data subject")
    record_id: Optional[str] = Field(default=None, description="Affected data record")
    regulation: str = Field(description="Regulation violated (GDPR, CCPA, etc.)")
    description: str = Field(description="Detailed description of violation")
    affected_data: Dict = Field(default_factory=dict, description="Data affected by violation")
    remediation_required: bool = Field(default=True, description="Whether remediation is required")
    remediation_deadline: Optional[datetime] = Field(default=None, description="Deadline for remediation")
    remediation_completed: bool = Field(default=False, description="Whether remediation was completed")
    remediation_details: Optional[str] = Field(default=None, description="Remediation action taken")


class RetentionPolicy(BaseModel):
    """Data retention policy configuration."""
    
    policy_id: str = Field(description="Unique policy identifier")
    name: str = Field(description="Policy name")
    data_category: DataCategory = Field(description="Data category this policy applies to")
    retention_period_days: int = Field(description="Retention period in days")
    auto_delete: bool = Field(default=True, description="Automatically delete after retention period")
    archive_before_delete: bool = Field(default=False, description="Archive data before deletion")
    requires_consent: bool = Field(default=True, description="Whether consent is required")
    legal_hold_exempt: bool = Field(default=False, description="Exempt from legal holds")
    geographic_restrictions: List[str] = Field(default_factory=list, description="Geographic restrictions")
    purpose_limitation: List[str] = Field(default_factory=list, description="Allowed purposes")


class GDPRComplianceManager:
    """GDPR compliance and data protection manager."""
    
    def __init__(self):
        self.data_subjects: Dict[str, DataSubject] = {}
        self.data_records: Dict[str, DataRecord] = {}
        self.audit_log: List[AuditLogEntry] = []
        self.violations: List[ComplianceViolation] = []
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.redis: Optional[aioredis.Redis] = None
        
        # Default retention policies
        self._setup_default_policies()
    
    def _setup_default_policies(self):
        """Setup default retention policies."""
        policies = [
            RetentionPolicy(
                policy_id="personal_data_default",
                name="Personal Data Default",
                data_category=DataCategory.PERSONAL_IDENTIFIABLE,
                retention_period_days=365,  # 1 year
                requires_consent=True,
                archive_before_delete=True
            ),
            RetentionPolicy(
                policy_id="technical_logs_default",
                name="Technical Logs Default",
                data_category=DataCategory.TECHNICAL_LOGS,
                retention_period_days=90,  # 3 months
                requires_consent=False,
                legal_hold_exempt=True
            ),
            RetentionPolicy(
                policy_id="security_logs_default",
                name="Security Logs Default",
                data_category=DataCategory.SECURITY_LOGS,
                retention_period_days=2555,  # 7 years
                requires_consent=False,
                legal_hold_exempt=False
            ),
            RetentionPolicy(
                policy_id="analytics_data_default",
                name="Analytics Data Default",
                data_category=DataCategory.ANALYTICS_DATA,
                retention_period_days=730,  # 2 years
                requires_consent=True,
                auto_delete=True
            ),
            RetentionPolicy(
                policy_id="performance_metrics_default",
                name="Performance Metrics Default",
                data_category=DataCategory.PERFORMANCE_METRICS,
                retention_period_days=180,  # 6 months
                requires_consent=False,
                auto_delete=True
            )
        ]
        
        for policy in policies:
            self.retention_policies[policy.policy_id] = policy
    
    async def initialize_redis(self):
        """Initialize Redis connection for persistent storage."""
        try:
            self.redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis for compliance data persistence")
        except Exception as e:
            logger.warning(f"Redis not available for compliance persistence: {e}")
    
    async def register_data_subject(self, ip_address: str, user_agent: str = None, 
                                   consent_given: bool = False) -> str:
        """Register a new data subject."""
        subject_id = hashlib.sha256(f"{ip_address}:{user_agent or ''}".encode()).hexdigest()
        
        if subject_id not in self.data_subjects:
            self.data_subjects[subject_id] = DataSubject(
                subject_id=subject_id,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_given=consent_given,
                consent_timestamp=datetime.utcnow() if consent_given else None
            )
            
            # Persist to Redis
            if self.redis:
                await self.redis.hset(
                    "compliance:subjects",
                    subject_id,
                    self.data_subjects[subject_id].json()
                )
        
        return subject_id
    
    async def record_data_processing(self, subject_id: str, data_category: DataCategory,
                                   purpose: str, data_content: Dict,
                                   lawful_basis: ProcessingLawfulBasis = ProcessingLawfulBasis.LEGITIMATE_INTERESTS,
                                   is_sensitive: bool = False) -> str:
        """Record data processing activity."""
        # Get retention policy
        policy_key = f"{data_category.value}_default"
        policy = self.retention_policies.get(policy_key)
        
        if not policy:
            # Log compliance violation
            await self._log_violation(
                ComplianceViolation(
                    violation_type="missing_retention_policy",
                    severity="high",
                    subject_id=subject_id,
                    regulation="GDPR",
                    description=f"No retention policy found for data category {data_category}",
                    affected_data={"category": data_category.value}
                )
            )
            retention_days = 30  # Default short retention
        else:
            retention_days = policy.retention_period_days
            
            # Check consent requirement
            if policy.requires_consent:
                subject = self.data_subjects.get(subject_id)
                if not subject or not subject.consent_given:
                    await self._log_violation(
                        ComplianceViolation(
                            violation_type="processing_without_consent",
                            severity="critical",
                            subject_id=subject_id,
                            regulation="GDPR",
                            description=f"Processing {data_category} data without consent",
                            affected_data={"category": data_category.value, "purpose": purpose}
                        )
                    )
        
        # Create data record
        record = DataRecord(
            subject_id=subject_id,
            data_category=data_category,
            lawful_basis=lawful_basis,
            purpose=purpose,
            data_content=data_content,
            retention_period_days=retention_days,
            is_sensitive=is_sensitive
        )
        
        self.data_records[record.record_id] = record
        
        # Persist to Redis
        if self.redis:
            await self.redis.hset(
                "compliance:records",
                record.record_id,
                record.json()
            )
        
        return record.record_id
    
    async def log_data_access(self, record_id: str, action: DataAction,
                            operator_id: str, ip_address: str,
                            endpoint: str, method: str,
                            user_agent: str = None, details: Dict = None) -> str:
        """Log data access for audit trail."""
        record = self.data_records.get(record_id)
        if not record:
            logger.warning(f"Attempted to log access to non-existent record: {record_id}")
            return None
        
        # Check if access violates any policies
        compliance_status = await self._check_access_compliance(record, action, details or {})
        
        # Create audit log entry
        audit_entry = AuditLogEntry(
            action=action,
            subject_id=record.subject_id,
            record_id=record_id,
            operator_id=operator_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            request_method=method,
            data_category=record.data_category,
            purpose=record.purpose,
            lawful_basis=record.lawful_basis,
            details=details or {},
            compliance_status=compliance_status
        )
        
        self.audit_log.append(audit_entry)
        
        # Update record access log
        record.access_log.append(f"{datetime.utcnow().isoformat()}:{action}:{operator_id}")
        
        # Persist to Redis
        if self.redis:
            await self.redis.lpush(
                "compliance:audit_log",
                audit_entry.json()
            )
            # Keep only recent entries
            await self.redis.ltrim("compliance:audit_log", 0, 100000)
        
        return audit_entry.entry_id
    
    async def _check_access_compliance(self, record: DataRecord, action: DataAction, details: Dict) -> ComplianceStatus:
        """Check if data access complies with policies."""
        # Check retention period
        if record.expires_at and datetime.utcnow() > record.expires_at:
            await self._log_violation(
                ComplianceViolation(
                    violation_type="access_to_expired_data",
                    severity="high",
                    subject_id=record.subject_id,
                    record_id=record.record_id,
                    regulation="GDPR",
                    description="Attempted access to data past retention period",
                    affected_data={"action": action.value, "expired_date": record.expires_at.isoformat()}
                )
            )
            return ComplianceStatus.NON_COMPLIANT
        
        # Check consent for sensitive data
        if record.is_sensitive or record.data_category == DataCategory.PERSONAL_IDENTIFIABLE:
            subject = self.data_subjects.get(record.subject_id)
            if subject and subject.consent_withdrawn:
                await self._log_violation(
                    ComplianceViolation(
                        violation_type="access_after_consent_withdrawal",
                        severity="critical",
                        subject_id=record.subject_id,
                        record_id=record.record_id,
                        regulation="GDPR",
                        description="Attempted access to data after consent withdrawal",
                        affected_data={"action": action.value, "withdrawal_date": subject.consent_withdrawn.isoformat()}
                    )
                )
                return ComplianceStatus.NON_COMPLIANT
        
        return ComplianceStatus.COMPLIANT
    
    async def _log_violation(self, violation: ComplianceViolation):
        """Log compliance violation."""
        self.violations.append(violation)
        
        # Set remediation deadline
        if not violation.remediation_deadline:
            days_map = {"low": 30, "medium": 14, "high": 7, "critical": 1}
            deadline_days = days_map.get(violation.severity, 7)
            violation.remediation_deadline = datetime.utcnow() + timedelta(days=deadline_days)
        
        # Log to application logs
        level_map = {"low": logging.INFO, "medium": logging.WARNING, "high": logging.ERROR, "critical": logging.CRITICAL}
        level = level_map.get(violation.severity, logging.WARNING)
        
        logger.log(level, f"Compliance violation: {violation.violation_type} - {violation.description}")
        
        # Persist to Redis
        if self.redis:
            await self.redis.lpush("compliance:violations", violation.json())
    
    async def process_data_subject_request(self, subject_id: str, request_type: str, details: Dict = None) -> Dict:
        """Process data subject rights requests (GDPR Article 15-22)."""
        subject = self.data_subjects.get(subject_id)
        if not subject:
            return {"error": "Data subject not found", "subject_id": subject_id}
        
        result = {"request_type": request_type, "subject_id": subject_id, "processed_at": datetime.utcnow()}
        
        if request_type == "access":  # Right of access (Article 15)
            subject_records = [r for r in self.data_records.values() if r.subject_id == subject_id]
            result["data"] = {
                "subject_info": subject.dict(),
                "records": [
                    {
                        "record_id": r.record_id,
                        "category": r.data_category,
                        "purpose": r.purpose,
                        "created_at": r.created_at,
                        "expires_at": r.expires_at,
                        "lawful_basis": r.lawful_basis
                    } for r in subject_records
                ],
                "audit_trail": [
                    a.dict() for a in self.audit_log 
                    if a.subject_id == subject_id
                ]
            }
        
        elif request_type == "portability":  # Right to data portability (Article 20)
            subject_records = [r for r in self.data_records.values() 
                             if r.subject_id == subject_id and 
                             r.lawful_basis in (ProcessingLawfulBasis.CONSENT, ProcessingLawfulBasis.CONTRACT)]
            result["data"] = {
                "portable_data": [
                    {
                        "record_id": r.record_id,
                        "data": r.data_content,
                        "created_at": r.created_at,
                        "purpose": r.purpose
                    } for r in subject_records
                ]
            }
        
        elif request_type == "rectification":  # Right to rectification (Article 16)
            corrections = details.get("corrections", {})
            updated_records = []
            
            for record_id, new_data in corrections.items():
                if record_id in self.data_records:
                    record = self.data_records[record_id]
                    if record.subject_id == subject_id:
                        record.data_content.update(new_data)
                        record.updated_at = datetime.utcnow()
                        updated_records.append(record_id)
            
            result["updated_records"] = updated_records
        
        elif request_type == "erasure":  # Right to erasure (Article 17)
            deleted_records = []
            for record_id, record in list(self.data_records.items()):
                if record.subject_id == subject_id:
                    # Check if erasure is permitted
                    if self._can_erase_record(record):
                        del self.data_records[record_id]
                        deleted_records.append(record_id)
            
            result["deleted_records"] = deleted_records
        
        elif request_type == "restrict_processing":  # Right to restriction (Article 18)
            # Mark records as restricted
            restricted_records = []
            for record in self.data_records.values():
                if record.subject_id == subject_id:
                    record.data_content["_processing_restricted"] = True
                    record.updated_at = datetime.utcnow()
                    restricted_records.append(record.record_id)
            
            result["restricted_records"] = restricted_records
        
        elif request_type == "object":  # Right to object (Article 21)
            # Update subject preferences
            subject.opt_out_requests.append(f"{datetime.utcnow().isoformat()}:{details.get('objection_reason', 'general')}")
            
            # Stop processing based on legitimate interests
            affected_records = []
            for record in self.data_records.values():
                if (record.subject_id == subject_id and 
                    record.lawful_basis == ProcessingLawfulBasis.LEGITIMATE_INTERESTS):
                    record.data_content["_processing_objected"] = True
                    record.updated_at = datetime.utcnow()
                    affected_records.append(record.record_id)
            
            result["objection_applied"] = affected_records
        
        # Log the request processing
        await self.log_data_access(
            record_id="data_subject_request",
            action=DataAction.READ,
            operator_id="system",
            ip_address=details.get("requester_ip", "system"),
            endpoint="/compliance/data_subject_request",
            method="POST",
            details={"request_type": request_type, "subject_id": subject_id}
        )
        
        return result
    
    def _can_erase_record(self, record: DataRecord) -> bool:
        """Check if record can be erased under GDPR."""
        # Records required for legal obligations cannot be erased
        if record.lawful_basis == ProcessingLawfulBasis.LEGAL_OBLIGATION:
            return False
        
        # Security logs may have different rules
        if record.data_category == DataCategory.SECURITY_LOGS:
            return False  # Usually retained for security purposes
        
        return True
    
    async def run_retention_cleanup(self) -> Dict:
        """Run automated retention policy cleanup."""
        now = datetime.utcnow()
        cleanup_stats = {
            "deleted_records": 0,
            "archived_records": 0,
            "errors": []
        }
        
        for record_id, record in list(self.data_records.items()):
            if record.expires_at and now > record.expires_at:
                try:
                    # Check if archiving is required
                    policy = self.retention_policies.get(f"{record.data_category.value}_default")
                    
                    if policy and policy.archive_before_delete:
                        # Archive logic would go here
                        cleanup_stats["archived_records"] += 1
                    
                    # Delete record
                    del self.data_records[record_id]
                    cleanup_stats["deleted_records"] += 1
                    
                    # Log retention action
                    await self.log_data_access(
                        record_id=record_id,
                        action=DataAction.DELETE,
                        operator_id="retention_system",
                        ip_address="system",
                        endpoint="/compliance/retention_cleanup",
                        method="SYSTEM",
                        details={"reason": "retention_policy_expiry"}
                    )
                
                except Exception as e:
                    cleanup_stats["errors"].append(f"Failed to cleanup {record_id}: {str(e)}")
                    logger.error(f"Retention cleanup error for {record_id}: {e}")
        
        return cleanup_stats
    
    def get_compliance_report(self) -> Dict:
        """Generate comprehensive compliance report."""
        now = datetime.utcnow()
        
        # Count records by category
        category_counts = {}
        expired_records = 0
        sensitive_records = 0
        
        for record in self.data_records.values():
            category = record.data_category.value
            category_counts[category] = category_counts.get(category, 0) + 1
            
            if record.expires_at and now > record.expires_at:
                expired_records += 1
            
            if record.is_sensitive:
                sensitive_records += 1
        
        # Count violations by severity
        violation_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for violation in self.violations:
            violation_counts[violation.severity] += 1
        
        # Count data subjects with/without consent
        subjects_with_consent = sum(1 for s in self.data_subjects.values() if s.consent_given)
        subjects_without_consent = len(self.data_subjects) - subjects_with_consent
        
        return {
            "report_generated_at": now.isoformat(),
            "data_subjects": {
                "total": len(self.data_subjects),
                "with_consent": subjects_with_consent,
                "without_consent": subjects_without_consent
            },
            "data_records": {
                "total": len(self.data_records),
                "by_category": category_counts,
                "expired": expired_records,
                "sensitive": sensitive_records
            },
            "violations": {
                "total": len(self.violations),
                "by_severity": violation_counts,
                "unresolved": sum(1 for v in self.violations if not v.remediation_completed)
            },
            "audit_log_entries": len(self.audit_log),
            "retention_policies": len(self.retention_policies),
            "compliance_status": self._assess_overall_compliance()
        }
    
    def _assess_overall_compliance(self) -> str:
        """Assess overall compliance status."""
        critical_violations = sum(1 for v in self.violations 
                                if v.severity == "critical" and not v.remediation_completed)
        high_violations = sum(1 for v in self.violations 
                            if v.severity == "high" and not v.remediation_completed)
        
        if critical_violations > 0:
            return "NON_COMPLIANT"
        elif high_violations > 3:
            return "REQUIRES_IMMEDIATE_ATTENTION"
        elif high_violations > 0:
            return "REQUIRES_REVIEW"
        else:
            return "COMPLIANT"


# Global compliance manager instance
compliance_manager = GDPRComplianceManager()


async def compliance_middleware(request: Request):
    """Middleware to ensure compliance monitoring."""
    # Register data subject if not exists
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    
    subject_id = await compliance_manager.register_data_subject(
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Add to request state for use in endpoints
    request.state.compliance_subject_id = subject_id
    
    return {"subject_id": subject_id}