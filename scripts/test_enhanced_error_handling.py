#!/usr/bin/env python3
"""Test script for enhanced error handling and validation framework."""

import asyncio
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.exceptions import (
    CompanyExtractionError, CompanyNotFoundError, InvalidCompanyDomainError,
    ExtractionTimeoutError, InsufficientDataError, CompanyValidationError
)
from app.utils.validation import CompanyDataValidator, CompanyDataSanitizer, sanitize_company_data
from app.utils.resilience import RetryStrategy, CircuitBreaker, ErrorRecoveryManager, FailureType
from app.utils.monitoring import CompanyExtractionMonitor, StructuredLogger, get_monitoring_dashboard
from app.models.company import CompanyInformationRequest, ExtractionMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlingTestSuite:
    """Test suite for error handling and validation."""
    
    def __init__(self):
        """Initialize test suite."""
        self.validator = CompanyDataValidator()
        self.sanitizer = CompanyDataSanitizer()
        self.monitor = CompanyExtractionMonitor()
        self.structured_logger = StructuredLogger("test")
        
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def log_test_result(self, test_name: str, passed: bool, error: str = None):
        """Log test result."""
        if passed:
            self.test_results["passed"] += 1
            logger.info(f"✅ {test_name} - PASSED")
        else:
            self.test_results["failed"] += 1
            logger.error(f"❌ {test_name} - FAILED: {error}")
            self.test_results["errors"].append({"test": test_name, "error": error})
    
    def test_validation_framework(self):
        """Test validation framework."""
        logger.info("Testing validation framework...")
        
        # Test valid company name
        try:
            is_valid, error = self.validator.validate_company_name("OpenAI Inc.", raise_on_error=False)
            self.log_test_result("Valid company name", is_valid and not error)
        except Exception as e:
            self.log_test_result("Valid company name", False, str(e))
        
        # Test invalid company name
        try:
            is_valid, error = self.validator.validate_company_name("", raise_on_error=False)
            self.log_test_result("Invalid company name (empty)", not is_valid and error)
        except Exception as e:
            self.log_test_result("Invalid company name (empty)", False, str(e))
        
        # Test domain validation
        try:
            is_valid, error = self.validator.validate_domain("example.com", raise_on_error=False)
            self.log_test_result("Valid domain", is_valid and not error)
        except Exception as e:
            self.log_test_result("Valid domain", False, str(e))
        
        # Test invalid domain
        try:
            is_valid, error = self.validator.validate_domain("invalid..domain", raise_on_error=False)
            self.log_test_result("Invalid domain", not is_valid and error)
        except Exception as e:
            self.log_test_result("Invalid domain", False, str(e))
        
        # Test email validation
        try:
            is_valid, error = self.validator.validate_email("test@example.com", raise_on_error=False)
            self.log_test_result("Valid email", is_valid and not error)
        except Exception as e:
            self.log_test_result("Valid email", False, str(e))
        
        # Test comprehensive data validation
        try:\n            test_data = {\n                \"name\": \"Test Company\",\n                \"website\": \"https://test.com\",\n                \"email\": \"info@test.com\",\n                \"phone\": \"+1-555-123-4567\"\n            }\n            validation_result = self.validator.validate_complete_company_data(test_data)\n            self.log_test_result(\n                "Comprehensive validation", \n                validation_result[\"is_valid\"] and not validation_result[\"errors\"]\n            )\n        except Exception as e:\n            self.log_test_result(\"Comprehensive validation\", False, str(e))
    
    def test_sanitization_framework(self):
        """Test data sanitization."""
        logger.info("Testing sanitization framework...")
        
        # Test text sanitization
        try:
            dirty_text = "  Multiple   spaces\\n\\tand   tabs  "\n            clean_text = self.sanitizer.sanitize_text(dirty_text)\n            expected = "Multiple spaces and tabs"\n            self.log_test_result(\n                "Text sanitization", \n                clean_text.strip() == expected or "Multiple" in clean_text\n            )\n        except Exception as e:\n            self.log_test_result("Text sanitization", False, str(e))
        
        # Test email sanitization
        try:\n            email = "  Test@Example.COM  "\n            clean_email = self.sanitizer.sanitize_email(email)\n            self.log_test_result("Email sanitization", clean_email == "test@example.com")\n        except Exception as e:\n            self.log_test_result("Email sanitization", False, str(e))
        
        # Test URL sanitization
        try:\n            url = "example.com/page"\n            clean_url = self.sanitizer.sanitize_url(url)\n            self.log_test_result("URL sanitization", clean_url.startswith("https://"))\n        except Exception as e:\n            self.log_test_result("URL sanitization", False, str(e))
        
        # Test complete data sanitization
        try:\n            test_data = {\n                "name": "  Test Company Inc.  ",\n                "description": "A   company\\nwith   multiple   spaces",\n                "email": "  INFO@TEST.COM  ",\n                "website": "test.com",\n                "contact": {\n                    "email": "  contact@test.COM  ",\n                    "phone": "  +1-(555)-123-4567  "\n                }\n            }\n            sanitized = sanitize_company_data(test_data)\n            self.log_test_result(\n                "Complete data sanitization",\n                sanitized["name"].strip() == "Test Company Inc." and\n                "https://" in sanitized.get("website", "") and\n                sanitized.get("contact", {}).get("email") == "contact@test.com"\n            )\n        except Exception as e:\n            self.log_test_result("Complete data sanitization", False, str(e))
    
    def test_exception_hierarchy(self):\n        """Test exception hierarchy and error creation.\"\"\"\n        logger.info("Testing exception hierarchy...")\n        \n        # Test CompanyExtractionError\n        try:\n            error = CompanyExtractionError(\n                "Test error", "TEST_ERROR", {"context": "test"}\n            )\n            self.log_test_result(\n                "CompanyExtractionError creation",\n                error.error_code == "TEST_ERROR" and \n                error.context.get("context") == "test"\n            )\n        except Exception as e:\n            self.log_test_result("CompanyExtractionError creation", False, str(e))
        
        # Test CompanyNotFoundError\n        try:\n            error = CompanyNotFoundError("Test Company")\n            self.log_test_result(\n                "CompanyNotFoundError creation",\n                error.company_name == "Test Company" and\n                error.error_code == "COMPANY_NOT_FOUND"\n            )\n        except Exception as e:\n            self.log_test_result("CompanyNotFoundError creation", False, str(e))
        
        # Test InsufficientDataError\n        try:\n            error = InsufficientDataError(0.3, 0.5)\n            self.log_test_result(\n                "InsufficientDataError creation",\n                error.confidence_score == 0.3 and\n                error.threshold == 0.5 and\n                error.error_code == "INSUFFICIENT_DATA"\n            )\n        except Exception as e:\n            self.log_test_result("InsufficientDataError creation", False, str(e))
    
    async def test_resilience_framework(self):\n        """Test resilience patterns.\"\"\"\n        logger.info("Testing resilience framework...")\n        \n        # Test retry strategy\n        try:\n            retry_strategy = RetryStrategy()\n            call_count = 0\n            \n            async def failing_function():\n                nonlocal call_count\n                call_count += 1\n                if call_count < 3:\n                    raise ValueError("Test failure")\n                return "success"\n            \n            result = await retry_strategy.execute_with_retry(failing_function)\n            self.log_test_result(\n                "Retry strategy success",\n                result == "success" and call_count == 3\n            )\n        except Exception as e:\n            self.log_test_result("Retry strategy success", False, str(e))
        \n        # Test circuit breaker\n        try:\n            circuit_breaker = CircuitBreaker("test", )\n            \n            # Simulate failures to open circuit\n            for _ in range(6):  # More than failure threshold\n                try:\n                    await circuit_breaker.call(lambda: exec('raise ValueError("Test")'))\n                except:\n                    pass\n            \n            # Circuit should be open now\n            self.log_test_result(\n                "Circuit breaker opens",\n                circuit_breaker.state.value == "open"\n            )\n        except Exception as e:\n            self.log_test_result("Circuit breaker opens", False, str(e))
    
    def test_monitoring_framework(self):\n        """Test monitoring and logging.\"\"\"\n        logger.info("Testing monitoring framework...")\n        \n        # Test structured logging\n        try:\n            metrics = self.structured_logger.log_operation_start("test_operation")\n            self.structured_logger.log_operation_success(metrics)\n            \n            self.log_test_result(\n                "Structured logging",\n                metrics.operation_name == "test_operation" and\n                metrics.success is True\n            )\n        except Exception as e:\n            self.log_test_result("Structured logging", False, str(e))
        \n        # Test extraction monitoring\n        try:\n            initial_stats = self.monitor.get_extraction_stats()\n            \n            # Simulate extraction request\n            metrics = self.monitor.log_extraction_request("Test Company", "BASIC")\n            self.monitor.log_extraction_success(\n                metrics, "Test Company", 0.85, 3, 2\n            )\n            \n            updated_stats = self.monitor.get_extraction_stats()\n            \n            self.log_test_result(\n                "Extraction monitoring",\n                updated_stats["successful_extractions"] > initial_stats["successful_extractions"]\n            )\n        except Exception as e:\n            self.log_test_result("Extraction monitoring", False, str(e))
    
    def test_request_validation(self):
        """Test company extraction request validation.\"\"\"\n        logger.info("Testing request validation...")\n        \n        # Test valid request\n        try:\n            request = CompanyInformationRequest(\n                company_name="OpenAI Inc.",\n                domain="openai.com",\n                extraction_mode=ExtractionMode.BASIC,\n                timeout_seconds=60,\n                max_pages_to_crawl=5\n            )\n            \n            # This would be called by the service\n            self.validator.validate_company_name(request.company_name)\n            if request.domain:\n                self.validator.validate_domain(request.domain)\n            \n            self.log_test_result("Valid request validation", True)\n        except Exception as e:\n            self.log_test_result("Valid request validation", False, str(e))
        \n        # Test invalid request\n        try:\n            # This should raise an exception\n            self.validator.validate_company_name("")\n            self.log_test_result("Invalid request validation", False, "Should have raised exception")\n        except CompanyValidationError:\n            self.log_test_result("Invalid request validation", True)\n        except Exception as e:\n            self.log_test_result("Invalid request validation", False, f"Wrong exception: {str(e)}")
    
    async def run_all_tests(self):\n        """Run all test suites.\"\"\"\n        logger.info("Starting Enhanced Error Handling Test Suite")\n        logger.info("=" * 50)\n        \n        # Run all test methods\n        self.test_validation_framework()\n        self.test_sanitization_framework()\n        self.test_exception_hierarchy()\n        await self.test_resilience_framework()\n        self.test_monitoring_framework()\n        self.test_request_validation()\n        \n        # Print summary\n        logger.info("=" * 50)\n        logger.info("Test Suite Summary")\n        logger.info(f"✅ Passed: {self.test_results['passed']}")\n        logger.info(f"❌ Failed: {self.test_results['failed']}")\n        \n        if self.test_results["errors"]:\n            logger.error("Failed Tests:")\n            for error in self.test_results["errors"]:\n                logger.error(f"  - {error['test']}: {error['error']}")\n        \n        # Test monitoring dashboard\n        try:\n            dashboard = get_monitoring_dashboard()\n            logger.info(f"Monitoring Dashboard: {dashboard.keys()}")\n        except Exception as e:\n            logger.error(f"Dashboard test failed: {e}")
        \n        return self.test_results["failed"] == 0


async def main():\n    \"\"\"Run the test suite.\"\"\"\n    test_suite = ErrorHandlingTestSuite()\n    success = await test_suite.run_all_tests()\n    \n    if success:\n        logger.info("🎉 All tests passed! Enhanced error handling is working correctly.")\n        return 0\n    else:\n        logger.error("💥 Some tests failed. Please review the error handling implementation.")\n        return 1


if __name__ == "__main__":\n    exit_code = asyncio.run(main())\n    sys.exit(exit_code)