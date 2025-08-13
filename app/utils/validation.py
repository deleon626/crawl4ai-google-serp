"""Enhanced validation utilities for company extraction."""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse
from pydantic import BaseModel, validator, Field

from app.utils.exceptions import CompanyValidationError, InvalidCompanyDomainError

logger = logging.getLogger(__name__)


class CompanyValidationRules:
    """Centralized validation rules for company data."""
    
    # Required fields for basic company validation
    REQUIRED_BASIC_FIELDS = ['name']
    OPTIONAL_BASIC_FIELDS = ['description', 'website', 'industry', 'founded_year']
    
    # Required fields for contact validation
    REQUIRED_CONTACT_FIELDS = []
    OPTIONAL_CONTACT_FIELDS = ['email', 'phone', 'address', 'city', 'country']
    
    # Data quality thresholds
    MIN_CONFIDENCE_SCORE = 0.3
    MIN_QUALITY_SCORE = 0.4
    MIN_COMPLETENESS_SCORE = 0.5
    
    # Text length limits
    MAX_COMPANY_NAME_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_ADDRESS_LENGTH = 500
    
    # Regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^[\+]?[1-9]?[\d\s\-\(\)\.]{7,15}$')
    DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')


class CompanyDataValidator:
    """Comprehensive validator for company information."""
    
    def __init__(self, rules: CompanyValidationRules = None):
        """Initialize validator with rules."""
        self.rules = rules or CompanyValidationRules()
        
    def validate_company_name(self, name: str, raise_on_error: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate company name format and content.
        
        Args:
            name: Company name to validate
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not isinstance(name, str):
            error_msg = "Company name is required and must be a string"
            if raise_on_error:
                raise CompanyValidationError("name", name, error_msg)
            return False, error_msg
        
        name = name.strip()
        
        # Length validation
        if len(name) < 2:
            error_msg = "Company name must be at least 2 characters long"
            if raise_on_error:
                raise CompanyValidationError("name", name, error_msg)
            return False, error_msg
            
        if len(name) > self.rules.MAX_COMPANY_NAME_LENGTH:
            error_msg = f"Company name must be less than {self.rules.MAX_COMPANY_NAME_LENGTH} characters"
            if raise_on_error:
                raise CompanyValidationError("name", name, error_msg)
            return False, error_msg
        
        # Pattern validation (allow letters, numbers, spaces, and common business symbols)
        if not re.match(r'^[\w\s\-\.,&()\'\"]+$', name):
            error_msg = "Company name contains invalid characters"
            if raise_on_error:
                raise CompanyValidationError("name", name, error_msg)
            return False, error_msg
        
        return True, None
    
    def validate_domain(self, domain: str, raise_on_error: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate domain format.
        
        Args:
            domain: Domain to validate
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not domain:
            return True, None  # Domain is optional
            
        if not isinstance(domain, str):
            error_msg = "Domain must be a string"
            if raise_on_error:
                raise InvalidCompanyDomainError(str(domain), error_msg)
            return False, error_msg
        
        # Normalize domain
        normalized_domain = self._normalize_domain(domain)
        
        # Validate format
        if not self.rules.DOMAIN_PATTERN.match(normalized_domain):
            error_msg = f"Invalid domain format: '{domain}'"
            if raise_on_error:
                raise InvalidCompanyDomainError(domain, error_msg)
            return False, error_msg
        
        # Length validation
        if len(normalized_domain) > 253:
            error_msg = f"Domain is too long: '{domain}'"
            if raise_on_error:
                raise InvalidCompanyDomainError(domain, error_msg)
            return False, error_msg
        
        return True, None
    
    def validate_email(self, email: str, raise_on_error: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.
        
        Args:
            email: Email to validate
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return True, None  # Email is optional
            
        if not isinstance(email, str):
            error_msg = "Email must be a string"
            if raise_on_error:
                raise CompanyValidationError("email", email, error_msg)
            return False, error_msg
        
        email = email.strip().lower()
        
        if not self.rules.EMAIL_PATTERN.match(email):
            error_msg = f"Invalid email format: '{email}'"
            if raise_on_error:
                raise CompanyValidationError("email", email, error_msg)
            return False, error_msg
        
        return True, None
    
    def validate_phone(self, phone: str, raise_on_error: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return True, None  # Phone is optional
            
        if not isinstance(phone, str):
            error_msg = "Phone number must be a string"
            if raise_on_error:
                raise CompanyValidationError("phone", phone, error_msg)
            return False, error_msg
        
        # Remove common formatting
        cleaned_phone = re.sub(r'[^\d\+\-\(\)\s\.]', '', phone.strip())
        
        if not self.rules.PHONE_PATTERN.match(cleaned_phone):
            error_msg = f"Invalid phone number format: '{phone}'"
            if raise_on_error:
                raise CompanyValidationError("phone", phone, error_msg)
            return False, error_msg
        
        return True, None
    
    def validate_url(self, url: str, raise_on_error: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return True, None  # URL is optional
            
        if not isinstance(url, str):
            error_msg = "URL must be a string"
            if raise_on_error:
                raise CompanyValidationError("url", url, error_msg)
            return False, error_msg
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError("Missing scheme or netloc")
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Invalid scheme")
        except Exception:
            error_msg = f"Invalid URL format: '{url}'"
            if raise_on_error:
                raise CompanyValidationError("url", url, error_msg)
            return False, error_msg
        
        return True, None
    
    def validate_confidence_threshold(self, confidence: float, threshold: float = None) -> bool:
        """
        Validate confidence score meets threshold.
        
        Args:
            confidence: Confidence score to validate
            threshold: Minimum threshold (uses default if None)
            
        Returns:
            Whether confidence meets threshold
        """
        threshold = threshold or self.rules.MIN_CONFIDENCE_SCORE
        return confidence >= threshold
    
    def validate_complete_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive validation of company data.
        
        Args:
            data: Company data to validate
            
        Returns:
            Validation result with details
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "field_validations": {},
            "data_quality": {}
        }
        
        # Validate company name (required)
        try:
            name_valid, name_error = self.validate_company_name(data.get('name'), raise_on_error=False)
            validation_result["field_validations"]["name"] = {"valid": name_valid, "error": name_error}
            if not name_valid:
                validation_result["errors"].append(name_error)
                validation_result["is_valid"] = False
        except Exception as e:
            validation_result["errors"].append(f"Name validation error: {str(e)}")
            validation_result["is_valid"] = False
        
        # Validate optional fields
        optional_validations = [
            ("domain", self.validate_domain),
            ("email", self.validate_email),
            ("phone", self.validate_phone),
            ("website", self.validate_url)
        ]
        
        for field_name, validator_func in optional_validations:
            field_value = data.get(field_name)
            if field_value:
                try:
                    is_valid, error_msg = validator_func(field_value, raise_on_error=False)
                    validation_result["field_validations"][field_name] = {"valid": is_valid, "error": error_msg}
                    if not is_valid:
                        validation_result["warnings"].append(error_msg)
                except Exception as e:
                    validation_result["warnings"].append(f"{field_name.title()} validation error: {str(e)}")
        
        # Assess data quality
        validation_result["data_quality"] = self._assess_data_quality(data)
        
        # Check quality thresholds
        if validation_result["data_quality"]["quality_score"] < self.rules.MIN_QUALITY_SCORE:
            validation_result["warnings"].append(
                f"Data quality score {validation_result['data_quality']['quality_score']:.2f} "
                f"below recommended threshold {self.rules.MIN_QUALITY_SCORE}"
            )
        
        return validation_result
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain format."""
        domain = domain.lower().strip()
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.rstrip('/')
        return domain
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Union[float, str, List[str]]]:
        """Assess overall data quality."""
        quality_score = 0.0
        completeness_score = 0.0
        issues = []
        
        # Basic fields assessment (60% weight)
        basic_fields = self.rules.REQUIRED_BASIC_FIELDS + self.rules.OPTIONAL_BASIC_FIELDS
        basic_present = sum(1 for field in basic_fields if data.get(field))
        basic_completeness = basic_present / len(basic_fields)
        quality_score += basic_completeness * 0.6
        completeness_score += basic_completeness * 0.5
        
        if basic_completeness < 0.5:
            issues.append("Limited basic company information available")
        
        # Contact fields assessment (40% weight)
        contact_data = data.get('contact', {})
        contact_fields = self.rules.OPTIONAL_CONTACT_FIELDS
        contact_present = sum(1 for field in contact_fields if contact_data.get(field))
        contact_completeness = contact_present / len(contact_fields) if contact_fields else 0
        quality_score += contact_completeness * 0.4
        completeness_score += contact_completeness * 0.5
        
        if contact_completeness < 0.3:
            issues.append("Limited contact information available")
        
        # Additional data assessment
        additional_data_types = ['social_media', 'key_personnel', 'financial_info']
        additional_present = sum(1 for field in additional_data_types if data.get(field))
        additional_completeness = additional_present / len(additional_data_types)
        
        if additional_completeness > 0.5:
            quality_score += 0.1  # Bonus for rich data
            completeness_score += 0.1
        
        # Quality level classification
        if quality_score >= 0.8:
            quality_level = "excellent"
        elif quality_score >= 0.6:
            quality_level = "good"
        elif quality_score >= 0.4:
            quality_level = "fair"
        else:
            quality_level = "poor"
        
        return {
            "quality_score": round(quality_score, 2),
            "completeness_score": round(completeness_score, 2),
            "quality_level": quality_level,
            "issues": issues,
            "field_completeness": {
                "basic_info": round(basic_completeness, 2),
                "contact_info": round(contact_completeness, 2),
                "additional_data": round(additional_completeness, 2)
            }
        }


class CompanyDataSanitizer:
    """Utilities for sanitizing and cleaning company data."""
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = None, allow_html: bool = False) -> str:
        """
        Sanitize text content.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length (truncate if exceeded)
            allow_html: Whether to preserve HTML tags
            
        Returns:
            Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove HTML tags unless allowed
        if not allow_html:
            text = re.sub(r'<[^>]+>', '', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email address."""
        if not email:
            return ""
        return email.strip().lower()
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Sanitize phone number."""
        if not phone:
            return ""
        # Keep only digits, plus, parentheses, hyphens, spaces, and dots
        return re.sub(r'[^\d\+\-\(\)\s\.]', '', phone.strip())
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL."""
        if not url:
            return ""
        
        url = url.strip()
        
        # Add protocol if missing
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    @staticmethod
    def sanitize_domain(domain: str) -> str:
        """Sanitize domain name."""
        if not domain:
            return ""
        
        domain = domain.lower().strip()
        domain = re.sub(r'^https?://', '', domain)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.rstrip('/')
        
        return domain


# Convenience functions for common validation tasks
def validate_company_extraction_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate company extraction request data."""
    validator = CompanyDataValidator()
    return validator.validate_complete_company_data(data)


def sanitize_company_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all fields in company data."""
    sanitizer = CompanyDataSanitizer()
    sanitized = {}
    
    # Sanitize basic fields
    for field in ['name', 'description', 'industry']:
        if data.get(field):
            sanitized[field] = sanitizer.sanitize_text(data[field])
    
    # Sanitize URLs
    for field in ['website']:
        if data.get(field):
            sanitized[field] = sanitizer.sanitize_url(data[field])
    
    # Sanitize domain
    if data.get('domain'):
        sanitized['domain'] = sanitizer.sanitize_domain(data['domain'])
    
    # Sanitize contact information
    if data.get('contact'):
        contact = data['contact']
        sanitized_contact = {}
        
        if contact.get('email'):
            sanitized_contact['email'] = sanitizer.sanitize_email(contact['email'])
        if contact.get('phone'):
            sanitized_contact['phone'] = sanitizer.sanitize_phone(contact['phone'])
        
        # Sanitize address fields
        for field in ['address', 'city', 'state', 'country']:
            if contact.get(field):
                sanitized_contact[field] = sanitizer.sanitize_text(contact[field])
        
        if sanitized_contact:
            sanitized['contact'] = sanitized_contact
    
    return {**data, **sanitized}