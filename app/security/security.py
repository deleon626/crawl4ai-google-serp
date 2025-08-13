"""
Comprehensive security hardening and data protection.

This module implements enterprise-grade security measures including
input validation, SQL injection prevention, XSS protection, secure headers,
API key management, and data encryption.
"""

import base64
import hashlib
import hmac
import logging
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote, unquote, urlparse

import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Request, Response, HTTPException, status
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings

logger = logging.getLogger(__name__)


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    
    # Encryption settings
    encryption_key: Optional[str] = Field(default=None, description="Master encryption key")
    key_rotation_days: int = Field(default=90, description="Days between key rotations")
    
    # Password security
    password_min_length: int = Field(default=12, description="Minimum password length")
    password_require_special: bool = Field(default=True, description="Require special characters")
    password_require_numbers: bool = Field(default=True, description="Require numbers")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    
    # Session security
    session_timeout_minutes: int = Field(default=60, description="Session timeout in minutes")
    max_concurrent_sessions: int = Field(default=5, description="Max concurrent sessions per user")
    
    # API security
    api_key_length: int = Field(default=64, description="API key length in bytes")
    api_key_rotation_days: int = Field(default=30, description="Days between API key rotations")
    require_https: bool = Field(default=True, description="Require HTTPS in production")
    
    # Input validation
    max_input_length: int = Field(default=10000, description="Maximum input field length")
    allowed_file_types: Set[str] = Field(default={"txt", "json", "csv"}, description="Allowed file types")
    max_file_size_mb: int = Field(default=10, description="Maximum file size in MB")
    
    # Security headers
    enable_hsts: bool = Field(default=True, description="Enable HTTP Strict Transport Security")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    enable_csp: bool = Field(default=True, description="Enable Content Security Policy")
    csp_policy: str = Field(
        default="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
        description="Content Security Policy"
    )


class SecurityViolation(BaseModel):
    """Security violation record."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    violation_type: str = Field(description="Type of security violation")
    client_ip: str = Field(description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent")
    endpoint: str = Field(description="Endpoint accessed")
    payload: Dict = Field(default_factory=dict, description="Request payload (sanitized)")
    severity: str = Field(description="Violation severity: low, medium, high, critical")
    blocked: bool = Field(description="Whether request was blocked")
    details: Dict = Field(default_factory=dict, description="Additional violation details")


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
        # Dangerous patterns
        self.sql_injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\b(or|and)\b\s+\d+\s*=\s*\d+)",
            r"(\b(or|and)\b\s+['\"]\w+['\"]\s*=\s*['\"]\w+['\"]])",
            r"(char|ascii|substring|length|mid|left|right)\s*\("
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>",
            r"<link[^>]*>"
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$(){}[\]\\]",
            r"\b(cat|ls|pwd|whoami|id|uname|ps|kill|rm|mv|cp|chmod|chown|sudo|su)\b",
            r"(\.\./|\.\.\\)",
            r"(/etc/passwd|/etc/shadow|/proc/)",
            r"(cmd|powershell|bash|sh|zsh)\s"
        ]
        
        self.path_traversal_patterns = [
            r"(\.\./|\.\.\\/)",
            r"(%2e%2e%2f|%2e%2e\/|\.\.%2f|%2e%2e%5c)",
            r"(\\\.\.\\|/\.\./)",
            r"(%252e%252e%252f|%c0%af)"
        ]
    
    def validate_and_sanitize(self, data: Any, field_name: str = "input") -> Tuple[Any, List[str]]:
        """
        Validate and sanitize input data.
        
        Returns:
            Tuple of (sanitized_data, violations)
        """
        violations = []
        
        if isinstance(data, str):
            return self._validate_string(data, field_name)
        elif isinstance(data, dict):
            return self._validate_dict(data, field_name)
        elif isinstance(data, list):
            return self._validate_list(data, field_name)
        else:
            return data, violations
    
    def _validate_string(self, value: str, field_name: str) -> Tuple[str, List[str]]:
        """Validate and sanitize string input."""
        violations = []
        original_value = value
        
        # Length check
        if len(value) > self.config.max_input_length:
            violations.append(f"Input too long: {field_name} ({len(value)} > {self.config.max_input_length})")
            value = value[:self.config.max_input_length]
        
        # SQL injection check
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                violations.append(f"Potential SQL injection in {field_name}")
                break
        
        # XSS check
        for pattern in self.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                violations.append(f"Potential XSS in {field_name}")
                # Sanitize XSS
                value = re.sub(pattern, "", value, flags=re.IGNORECASE)
        
        # Command injection check
        for pattern in self.command_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                violations.append(f"Potential command injection in {field_name}")
                break
        
        # Path traversal check
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                violations.append(f"Potential path traversal in {field_name}")
                break
        
        # URL decode check (prevent double encoding attacks)
        decoded = unquote(value)
        if decoded != value and any(re.search(p, decoded, re.IGNORECASE) for p in 
                                   self.sql_injection_patterns + self.xss_patterns):
            violations.append(f"Potential encoding evasion in {field_name}")
        
        return value, violations
    
    def _validate_dict(self, data: dict, field_name: str) -> Tuple[dict, List[str]]:
        """Validate dictionary input."""
        violations = []
        sanitized = {}
        
        for key, value in data.items():
            # Validate key
            key_sanitized, key_violations = self._validate_string(str(key), f"{field_name}.key")
            violations.extend(key_violations)
            
            # Validate value
            value_sanitized, value_violations = self.validate_and_sanitize(value, f"{field_name}.{key}")
            violations.extend(value_violations)
            
            sanitized[key_sanitized] = value_sanitized
        
        return sanitized, violations
    
    def _validate_list(self, data: list, field_name: str) -> Tuple[list, List[str]]:
        """Validate list input."""
        violations = []
        sanitized = []
        
        for i, item in enumerate(data):
            item_sanitized, item_violations = self.validate_and_sanitize(item, f"{field_name}[{i}]")
            violations.extend(item_violations)
            sanitized.append(item_sanitized)
        
        return sanitized, violations


class CryptoManager:
    """Encryption and cryptographic utilities."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.fernet: Optional[Fernet] = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with master key."""
        if not self.config.encryption_key:
            # Generate a new key for development
            key = Fernet.generate_key()
            logger.warning("No encryption key provided, generated temporary key")
            logger.warning("Set ENCRYPTION_KEY environment variable for production")
        else:
            # Use provided key
            try:
                key = base64.urlsafe_b64decode(self.config.encryption_key)
                if len(key) != 32:
                    # Derive key from provided string
                    key = self._derive_key(self.config.encryption_key.encode())
            except Exception:
                # Treat as password and derive key
                key = self._derive_key(self.config.encryption_key.encode())
        
        self.fernet = Fernet(base64.urlsafe_b64encode(key))
    
    def _derive_key(self, password: bytes, salt: bytes = None) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        if salt is None:
            salt = b"crawl4ai_security"  # Use fixed salt for deterministic keys
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        
        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not self.fernet:
            raise RuntimeError("Encryption not initialized")
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Invalid encrypted data")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False
    
    def generate_api_key(self) -> str:
        """Generate cryptographically secure API key."""
        key_bytes = secrets.token_bytes(self.config.api_key_length)
        return base64.urlsafe_b64encode(key_bytes).decode().rstrip('=')
    
    def generate_session_token(self) -> str:
        """Generate secure session token."""
        token_data = {
            "timestamp": int(time.time()),
            "random": secrets.token_hex(16)
        }
        
        token_string = f"{token_data['timestamp']}:{token_data['random']}"
        return self.encrypt(token_string)
    
    def verify_session_token(self, token: str) -> bool:
        """Verify session token and check expiry."""
        try:
            decrypted = self.decrypt(token)
            timestamp_str, _ = decrypted.split(":", 1)
            timestamp = int(timestamp_str)
            
            # Check if token expired
            max_age = self.config.session_timeout_minutes * 60
            if time.time() - timestamp > max_age:
                return False
            
            return True
        except Exception:
            return False
    
    def create_hmac_signature(self, data: str, secret: str) -> str:
        """Create HMAC signature for data integrity."""
        signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_hmac_signature(self, data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature."""
        expected_signature = self.create_hmac_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # HTTP Strict Transport Security
        if self.config.enable_hsts and self.config.require_https:
            response.headers["Strict-Transport-Security"] = f"max-age={self.config.hsts_max_age}; includeSubDomains"
        
        # Content Security Policy
        if self.config.enable_csp:
            response.headers["Content-Security-Policy"] = self.config.csp_policy
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server identification
        response.headers.pop("Server", None)
        
        # Add security-related headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Robots-Tag"] = "noindex, nofollow, nosnippet, noarchive"
        
        return response


class SecurityManager:
    """Main security management system."""
    
    def __init__(self):
        self.config = SecurityConfig()
        self.validator = InputValidator(self.config)
        self.crypto = CryptoManager(self.config)
        self.violations: List[SecurityViolation] = []
        self.max_violations_memory = 10000
        
        # Security patterns are imported at module level
    
    def configure(self, **kwargs):
        """Update security configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Reinitialize components if needed
        if any(k.startswith(('encryption', 'password', 'api_key')) for k in kwargs.keys()):
            self.crypto = CryptoManager(self.config)
    
    async def validate_request(self, request: Request) -> Tuple[bool, Dict]:
        """
        Comprehensive request validation.
        
        Returns:
            Tuple of (is_valid: bool, details: dict)
        """
        violations = []
        client_ip = self._get_client_ip(request)
        
        # HTTPS check in production
        if self.config.require_https and not settings.debug:
            if request.url.scheme != "https":
                violation = SecurityViolation(
                    violation_type="insecure_connection",
                    client_ip=client_ip,
                    endpoint=str(request.url.path),
                    severity="medium",
                    blocked=True,
                    details={"scheme": request.url.scheme}
                )
                await self._log_violation(violation)
                return False, {"error": "HTTPS required", "violation": "insecure_connection"}
        
        # Validate headers
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) > 1000:
            violation = SecurityViolation(
                violation_type="suspicious_user_agent",
                client_ip=client_ip,
                user_agent=user_agent,
                endpoint=str(request.url.path),
                severity="low",
                blocked=False,
                details={"user_agent_length": len(user_agent)}
            )
            violations.append(violation)
        
        # Check for suspicious headers
        suspicious_headers = {
            "x-forwarded-host": "host_header_injection",
            "x-real-ip": "ip_spoofing_attempt",
            "x-originating-ip": "ip_spoofing_attempt"
        }
        
        for header, violation_type in suspicious_headers.items():
            if header in request.headers:
                header_value = request.headers[header]
                if self._is_suspicious_header_value(header_value):
                    violation = SecurityViolation(
                        violation_type=violation_type,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        endpoint=str(request.url.path),
                        severity="medium",
                        blocked=False,
                        details={"header": header, "value": header_value[:100]}
                    )
                    violations.append(violation)
        
        # Validate query parameters
        for param, value in request.query_params.items():
            sanitized_value, param_violations = self.validator.validate_and_sanitize(value, f"query.{param}")
            
            if param_violations:
                violation = SecurityViolation(
                    violation_type="malicious_query_parameter",
                    client_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    payload={"parameter": param, "value": value[:100]},
                    severity="high",
                    blocked=True,
                    details={"violations": param_violations}
                )
                await self._log_violation(violation)
                return False, {
                    "error": "Malicious query parameter detected",
                    "parameter": param,
                    "violations": param_violations
                }
        
        # Validate request body if present
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    body = await request.json()
                    sanitized_body, body_violations = self.validator.validate_and_sanitize(body, "body")
                    
                    if body_violations:
                        violation = SecurityViolation(
                            violation_type="malicious_request_body",
                            client_ip=client_ip,
                            user_agent=user_agent,
                            endpoint=str(request.url.path),
                            payload={"body_sample": str(body)[:200]},
                            severity="high",
                            blocked=True,
                            details={"violations": body_violations}
                        )
                        await self._log_violation(violation)
                        return False, {
                            "error": "Malicious request body detected",
                            "violations": body_violations
                        }
            except Exception as e:
                logger.warning(f"Failed to validate request body: {e}")
        
        # Log non-blocking violations
        for violation in violations:
            await self._log_violation(violation)
        
        return True, {"violations": len(violations)}
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        return (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP") or
            request.client.host if request.client else "unknown"
        )
    
    def _is_suspicious_header_value(self, value: str) -> bool:
        """Check if header value is suspicious."""
        suspicious_patterns = [
            r"[<>\"'&]",  # HTML/script characters
            r"\.\./",  # Path traversal
            r"(http|https|ftp)://",  # URLs
            r"\b(eval|exec|system|shell_exec)\b",  # Code execution functions
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    async def _log_violation(self, violation: SecurityViolation):
        """Log security violation."""
        # Add to memory
        self.violations.append(violation)
        
        # Keep memory usage reasonable
        if len(self.violations) > self.max_violations_memory:
            self.violations = self.violations[-self.max_violations_memory // 2:]
        
        # Log to application logs
        level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }.get(violation.severity, logging.WARNING)
        
        logger.log(level, 
            f"Security violation: {violation.violation_type} from {violation.client_ip} "
            f"on {violation.endpoint} (blocked: {violation.blocked})")
    
    def get_violations(self, limit: int = 100, severity: str = None) -> List[SecurityViolation]:
        """Get recent security violations."""
        violations = self.violations
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        return sorted(violations, key=lambda v: v.timestamp, reverse=True)[:limit]
    
    def get_security_headers_middleware(self):
        """Get security headers middleware."""
        return SecurityHeadersMiddleware


# Global security manager instance
security_manager = SecurityManager()


async def security_validation_middleware(request: Request):
    """FastAPI dependency for security validation."""
    is_valid, details = await security_manager.validate_request(request)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=details
        )
    
    return details