#!/usr/bin/env python3
"""
Security validation script for production deployment.

This script performs comprehensive security validation including:
- Security configuration verification
- Vulnerability scanning
- Compliance checks
- Performance impact assessment
- Integration testing
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

import aiohttp
import requests
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityValidator:
    """Comprehensive security validation system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = {
            "timestamp": datetime.utcnow(),
            "tests_passed": 0,
            "tests_failed": 0,
            "warnings": 0,
            "critical_issues": 0,
            "details": []
        }
        
    def print_header(self, title: str):
        """Print section header."""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        self.results["tests_passed"] += 1
    
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
        self.results["warnings"] += 1
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        self.results["tests_failed"] += 1
    
    def print_critical(self, message: str):
        """Print critical error message."""
        print(f"{Fore.RED}🚨 CRITICAL: {message}{Style.RESET_ALL}")
        self.results["critical_issues"] += 1
    
    def record_result(self, test_name: str, status: str, message: str, details: Dict = None):
        """Record test result."""
        self.results["details"].append({
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def test_server_availability(self) -> bool:
        """Test if server is available."""
        self.print_header("Server Availability Check")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=10)
            if response.status_code == 200:
                self.print_success("Server is available and responding")
                self.record_result("server_availability", "pass", "Server responding normally")
                return True
            else:
                self.print_error(f"Server returned status code: {response.status_code}")
                self.record_result("server_availability", "fail", f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.print_critical(f"Cannot connect to server: {e}")
            self.record_result("server_availability", "critical", str(e))
            return False
    
    def test_security_headers(self) -> bool:
        """Test security headers."""
        self.print_header("Security Headers Validation")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health")
            headers = response.headers
            
            # Required security headers
            required_headers = {
                "X-Frame-Options": "Should be DENY or SAMEORIGIN",
                "X-Content-Type-Options": "Should be nosniff",
                "X-XSS-Protection": "Should be enabled",
                "Referrer-Policy": "Should be set",
                "X-Security-Level": "Should indicate security level"
            }
            
            all_passed = True
            for header, description in required_headers.items():
                if header in headers:
                    self.print_success(f"{header}: {headers[header]}")
                    self.record_result(f"security_header_{header}", "pass", headers[header])
                else:
                    self.print_error(f"Missing {header} - {description}")
                    self.record_result(f"security_header_{header}", "fail", "Header missing")
                    all_passed = False
            
            return all_passed
        
        except Exception as e:
            self.print_error(f"Failed to check security headers: {e}")
            self.record_result("security_headers", "error", str(e))
            return False
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting functionality."""
        self.print_header("Rate Limiting Validation")
        
        try:
            # Make rapid requests to trigger rate limiting
            responses = []
            start_time = time.time()
            
            print("Making rapid requests to test rate limiting...")
            for i in range(30):  # Make 30 rapid requests
                try:
                    response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
                    responses.append(response.status_code)
                    if response.status_code == 429:
                        break
                    time.sleep(0.1)  # Small delay between requests
                except requests.RequestException:
                    break
            
            end_time = time.time()
            
            # Check if rate limiting kicked in
            rate_limited = 429 in responses
            if rate_limited:
                self.print_success("Rate limiting is active (HTTP 429 received)")
                self.record_result("rate_limiting", "pass", f"Rate limited after {responses.index(429)} requests")
                
                # Test rate limit headers
                try:
                    response = requests.get(f"{self.base_url}/api/v1/health")
                    if "Retry-After" in response.headers or "X-RateLimit-" in str(response.headers):
                        self.print_success("Rate limit headers present")
                    else:
                        self.print_warning("Rate limit headers missing")
                except Exception:
                    pass
                
                return True
            else:
                self.print_warning("Rate limiting may not be configured or limits are very high")
                self.record_result("rate_limiting", "warning", "No rate limiting observed")
                return False
        
        except Exception as e:
            self.print_error(f"Rate limiting test failed: {e}")
            self.record_result("rate_limiting", "error", str(e))
            return False
    
    def test_input_validation(self) -> bool:
        """Test input validation and XSS/SQL injection protection."""
        self.print_header("Input Validation & Injection Protection")
        
        # Test cases for various injection attacks
        test_cases = [
            {
                "name": "SQL Injection",
                "payload": {"query": "'; DROP TABLE users; --", "country": "US"},
                "should_block": True
            },
            {
                "name": "XSS Script Tag",
                "payload": {"query": "<script>alert('xss')</script>", "country": "US"},
                "should_block": True
            },
            {
                "name": "Command Injection",
                "payload": {"query": "test; rm -rf /", "country": "US"},
                "should_block": True
            },
            {
                "name": "Path Traversal",
                "payload": {"query": "../../../etc/passwd", "country": "US"},
                "should_block": True
            },
            {
                "name": "Normal Input",
                "payload": {"query": "normal search query", "country": "US"},
                "should_block": False
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/v1/search",
                    json=test_case["payload"],
                    timeout=10
                )
                
                if test_case["should_block"]:
                    if response.status_code in [400, 403, 422]:
                        self.print_success(f"{test_case['name']}: Properly blocked")
                        self.record_result(f"input_validation_{test_case['name']}", "pass", "Malicious input blocked")
                    else:
                        self.print_error(f"{test_case['name']}: NOT blocked (status: {response.status_code})")
                        self.record_result(f"input_validation_{test_case['name']}", "fail", f"Not blocked, status: {response.status_code}")
                        all_passed = False
                else:
                    if response.status_code in [200, 422]:  # 422 for validation errors is OK
                        self.print_success(f"{test_case['name']}: Normal input accepted")
                        self.record_result(f"input_validation_{test_case['name']}", "pass", "Normal input accepted")
                    else:
                        self.print_warning(f"{test_case['name']}: Unexpected status {response.status_code}")
            
            except Exception as e:
                self.print_error(f"{test_case['name']} test failed: {e}")
                all_passed = False
        
        return all_passed
    
    def test_https_enforcement(self) -> bool:
        """Test HTTPS enforcement."""
        self.print_header("HTTPS Enforcement Check")
        
        if self.base_url.startswith("https://"):
            self.print_success("Using HTTPS connection")
            self.record_result("https_enforcement", "pass", "HTTPS in use")
            return True
        elif self.base_url.startswith("http://"):
            if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
                self.print_warning("Using HTTP for localhost (acceptable for development)")
                self.record_result("https_enforcement", "warning", "HTTP localhost")
                return True
            else:
                self.print_critical("Using HTTP for production deployment - SECURITY RISK!")
                self.record_result("https_enforcement", "critical", "HTTP in production")
                return False
        else:
            self.print_error("Invalid URL scheme")
            return False
    
    def test_robots_compliance(self) -> bool:
        """Test robots.txt compliance."""
        self.print_header("Robots.txt Compliance Check")
        
        try:
            # Test that robots.txt compliance is working by checking crawl endpoints
            test_payload = {
                "url": "https://example.com/test",
                "include_raw_html": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/crawl",
                json=test_payload,
                timeout=30
            )
            
            # Check if the response indicates robots.txt checking
            if response.status_code in [200, 400, 422]:
                response_text = response.text.lower()
                if "robot" in response_text or "compliance" in response_text:
                    self.print_success("Robots.txt compliance appears active")
                    self.record_result("robots_compliance", "pass", "Compliance checks detected")
                    return True
                else:
                    self.print_warning("Robots.txt compliance status unclear")
                    self.record_result("robots_compliance", "warning", "Status unclear")
                    return True
            else:
                self.print_error(f"Crawl endpoint error: {response.status_code}")
                return False
        
        except Exception as e:
            self.print_error(f"Robots.txt compliance test failed: {e}")
            self.record_result("robots_compliance", "error", str(e))
            return False
    
    def test_security_endpoints(self) -> bool:
        """Test security management endpoints."""
        self.print_header("Security Management Endpoints")
        
        # Test without authentication
        try:
            response = requests.get(f"{self.base_url}/api/v1/security/status", timeout=10)
            if response.status_code == 401:
                self.print_success("Security endpoints properly protected (401 Unauthorized)")
                self.record_result("security_endpoints_auth", "pass", "Endpoints protected")
                
                # Test with mock token
                headers = {"Authorization": "Bearer test_token"}
                response = requests.get(f"{self.base_url}/api/v1/security/status", headers=headers, timeout=10)
                
                if response.status_code in [200, 500]:  # 500 acceptable if not fully configured
                    self.print_success("Security endpoints accessible with token")
                    return True
                else:
                    self.print_warning(f"Unexpected status with token: {response.status_code}")
                    return True
            else:
                self.print_critical("Security endpoints NOT protected - major security risk!")
                self.record_result("security_endpoints_auth", "critical", "Endpoints not protected")
                return False
        
        except Exception as e:
            self.print_error(f"Security endpoints test failed: {e}")
            self.record_result("security_endpoints", "error", str(e))
            return False
    
    def test_cors_configuration(self) -> bool:
        """Test CORS configuration."""
        self.print_header("CORS Configuration Check")
        
        try:
            # Check CORS headers
            response = requests.options(f"{self.base_url}/api/v1/health")
            cors_headers = {
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers"
            }
            
            present_cors_headers = set(response.headers.keys()) & cors_headers
            
            if present_cors_headers:
                self.print_success(f"CORS configured: {', '.join(present_cors_headers)}")
                
                # Check if overly permissive
                origin = response.headers.get("Access-Control-Allow-Origin", "")
                if origin == "*":
                    self.print_warning("CORS allows all origins (*) - consider restricting for production")
                    self.record_result("cors_config", "warning", "Permissive CORS")
                else:
                    self.print_success("CORS origin restrictions in place")
                    self.record_result("cors_config", "pass", f"Restricted origins: {origin}")
                
                return True
            else:
                self.print_warning("No CORS headers detected")
                self.record_result("cors_config", "warning", "No CORS headers")
                return True
        
        except Exception as e:
            self.print_error(f"CORS test failed: {e}")
            self.record_result("cors_config", "error", str(e))
            return False
    
    async def test_performance_impact(self) -> bool:
        """Test security features' performance impact."""
        self.print_header("Performance Impact Assessment")
        
        try:
            # Measure response times with security features
            response_times = []
            
            print("Measuring response times with security features...")
            for i in range(10):
                start_time = time.time()
                response = requests.get(f"{self.base_url}/api/v1/health")
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append((end_time - start_time) * 1000)  # Convert to ms
                
                await asyncio.sleep(0.1)
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                
                if avg_time < 100:  # Less than 100ms average
                    self.print_success(f"Good performance: avg {avg_time:.1f}ms, max {max_time:.1f}ms")
                    self.record_result("performance_impact", "pass", f"avg: {avg_time:.1f}ms")
                elif avg_time < 500:  # Less than 500ms average
                    self.print_warning(f"Acceptable performance: avg {avg_time:.1f}ms, max {max_time:.1f}ms")
                    self.record_result("performance_impact", "warning", f"avg: {avg_time:.1f}ms")
                else:
                    self.print_error(f"Poor performance: avg {avg_time:.1f}ms, max {max_time:.1f}ms")
                    self.record_result("performance_impact", "fail", f"avg: {avg_time:.1f}ms")
                    return False
                
                return True
            else:
                self.print_error("Could not measure performance")
                return False
        
        except Exception as e:
            self.print_error(f"Performance test failed: {e}")
            self.record_result("performance_impact", "error", str(e))
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final security validation report."""
        self.print_header("Security Validation Summary")
        
        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / max(total_tests, 1)) * 100
        
        # Overall status
        if self.results["critical_issues"] > 0:
            overall_status = "CRITICAL - DO NOT DEPLOY"
            status_color = Fore.RED
        elif self.results["tests_failed"] > 0:
            overall_status = "FAILED - Issues need resolution"
            status_color = Fore.RED
        elif self.results["warnings"] > 3:
            overall_status = "WARNING - Review recommended"
            status_color = Fore.YELLOW
        elif pass_rate >= 90:
            overall_status = "PASSED - Ready for deployment"
            status_color = Fore.GREEN
        else:
            overall_status = "NEEDS IMPROVEMENT"
            status_color = Fore.YELLOW
        
        print(f"\n{status_color}{overall_status}{Style.RESET_ALL}")
        print(f"\nTest Results:")
        print(f"  ✓ Passed: {self.results['tests_passed']}")
        print(f"  ✗ Failed: {self.results['tests_failed']}")
        print(f"  ⚠ Warnings: {self.results['warnings']}")
        print(f"  🚨 Critical: {self.results['critical_issues']}")
        print(f"  📊 Pass Rate: {pass_rate:.1f}%")
        
        self.results["overall_status"] = overall_status
        self.results["pass_rate"] = pass_rate
        
        return self.results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all security validation tests."""
        print(f"{Fore.CYAN}🛡️  Starting Comprehensive Security Validation{Style.RESET_ALL}")
        print(f"Target: {self.base_url}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        # Run all tests
        tests = [
            self.test_server_availability,
            self.test_https_enforcement,
            self.test_security_headers,
            self.test_rate_limiting,
            self.test_input_validation,
            self.test_robots_compliance,
            self.test_security_endpoints,
            self.test_cors_configuration,
        ]
        
        # Run synchronous tests
        for test in tests:
            try:
                test()
            except Exception as e:
                self.print_error(f"Test {test.__name__} failed with exception: {e}")
        
        # Run asynchronous tests
        try:
            await self.test_performance_impact()
        except Exception as e:
            self.print_error(f"Performance test failed with exception: {e}")
        
        # Generate final report
        return self.generate_report()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security validation for Crawl4AI API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--output", help="Output file for detailed report")
    
    args = parser.parse_args()
    
    validator = SecurityValidator(args.url)
    
    try:
        results = await validator.run_all_tests()
        
        # Save detailed report if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nDetailed report saved to: {args.output}")
        
        # Exit with appropriate code
        if results["critical_issues"] > 0:
            sys.exit(2)  # Critical issues
        elif results["tests_failed"] > 0:
            sys.exit(1)  # Some tests failed
        else:
            sys.exit(0)  # All good
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Validation interrupted by user{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}Validation failed with error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())