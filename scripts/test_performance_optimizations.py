#!/usr/bin/env python3
"""
Performance optimization testing and validation script.

This script tests the performance optimizations implemented in the system,
including caching, concurrent processing, resource management, and batch processing.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

import httpx
import redis.asyncio as redis

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.caching import CompanyCacheService, CacheManager
from app.utils.resource_manager import ResourceManager, ResourceLimits
from app.utils.performance import PerformanceMonitor
from app.services.concurrent_extraction import ConcurrentExtractionService, ConcurrencyConfig
from app.services.batch_company_service import BatchCompanyService
from app.models.company import CompanyInformationRequest, ExtractionMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Comprehensive performance testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize test suite."""
        self.base_url = base_url
        self.results = {}
        
        # Test configuration
        self.test_companies = [
            "OpenAI", "Microsoft", "Google", "Apple", "Amazon",
            "Meta", "Tesla", "Netflix", "Uber", "Airbnb"
        ]
        
        logger.info(f"Performance test suite initialized with base URL: {base_url}")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests."""
        logger.info("Starting comprehensive performance test suite")
        
        test_start = time.time()
        
        # Test 1: Redis caching performance
        logger.info("Test 1: Testing Redis caching performance")
        self.results["caching"] = await self.test_caching_performance()
        
        # Test 2: Resource management
        logger.info("Test 2: Testing resource management")
        self.results["resource_management"] = await self.test_resource_management()
        
        # Test 3: Performance monitoring
        logger.info("Test 3: Testing performance monitoring")
        self.results["performance_monitoring"] = await self.test_performance_monitoring()
        
        # Test 4: Concurrent processing
        logger.info("Test 4: Testing concurrent processing")
        self.results["concurrent_processing"] = await self.test_concurrent_processing()
        
        # Test 5: API performance
        logger.info("Test 5: Testing API performance")
        self.results["api_performance"] = await self.test_api_performance()
        
        # Test 6: Batch processing (if API is available)
        logger.info("Test 6: Testing batch processing")
        self.results["batch_processing"] = await self.test_batch_processing()
        
        total_time = time.time() - test_start
        
        # Generate summary
        self.results["summary"] = {
            "total_test_time": total_time,
            "tests_completed": len(self.results) - 1,  # Exclude summary itself
            "overall_status": "completed",
            "test_timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Performance test suite completed in {total_time:.2f} seconds")
        return self.results
    
    async def test_caching_performance(self) -> Dict[str, Any]:
        """Test Redis caching performance."""
        try:
            cache_manager = CacheManager()
            cache_service = CompanyCacheService(cache_manager)
            
            async with cache_service:
                # Test cache operations
                test_data = {
                    "company_name": "TestCorp",
                    "basic_info": {"description": "Test company for caching"},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Test write performance
                write_times = []
                for i in range(10):
                    start_time = time.time()
                    await cache_service.set_company_info(f"test_company_{i}", test_data)
                    write_times.append(time.time() - start_time)
                
                # Test read performance
                read_times = []
                for i in range(10):
                    start_time = time.time()
                    result = await cache_service.get_company_info(f"test_company_{i}")
                    read_times.append(time.time() - start_time)
                    
                    if not result:
                        logger.warning(f"Cache miss for test_company_{i}")
                
                # Test SERP caching
                serp_times = []
                for i in range(5):
                    start_time = time.time()
                    await cache_service.set_serp_results(
                        f"test query {i}", "US", "en", 
                        {"results": [{"title": "Test", "url": "http://test.com"}]}
                    )
                    serp_times.append(time.time() - start_time)
                
                # Get cache statistics
                cache_stats = await cache_service.get_cache_stats()
                
                return {
                    "status": "success",
                    "write_performance": {
                        "avg_time": sum(write_times) / len(write_times),
                        "min_time": min(write_times),
                        "max_time": max(write_times)
                    },
                    "read_performance": {
                        "avg_time": sum(read_times) / len(read_times),
                        "min_time": min(read_times),
                        "max_time": max(read_times)
                    },
                    "serp_write_performance": {
                        "avg_time": sum(serp_times) / len(serp_times),
                        "operations": len(serp_times)
                    },
                    "cache_stats": cache_stats
                }
                
        except Exception as e:
            logger.error(f"Cache performance test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_resource_management(self) -> Dict[str, Any]:
        """Test resource management system."""
        try:
            limits = ResourceLimits(
                max_memory_mb=256,
                max_cpu_percent=70.0,
                max_open_connections=50
            )
            
            resource_manager = ResourceManager(limits)
            
            async with resource_manager:
                # Test resource monitoring
                await asyncio.sleep(1.0)  # Let monitoring collect data
                
                # Test HTTP requests
                request_times = []
                for i in range(5):
                    start_time = time.time()
                    try:
                        response = await resource_manager.make_request("GET", "https://httpbin.org/delay/1")
                        request_times.append(time.time() - start_time)
                    except Exception as e:
                        logger.warning(f"Request {i} failed: {e}")
                
                # Test memory optimization
                optimization_result = await resource_manager.optimize_resources()
                
                # Get resource status
                resource_status = await resource_manager.get_resource_status()
                
                return {
                    "status": "success",
                    "request_performance": {
                        "avg_time": sum(request_times) / len(request_times) if request_times else 0,
                        "successful_requests": len(request_times),
                        "total_attempts": 5
                    },
                    "optimization_result": optimization_result,
                    "resource_status": resource_status
                }
                
        except Exception as e:
            logger.error(f"Resource management test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_performance_monitoring(self) -> Dict[str, Any]:
        """Test performance monitoring system."""
        try:
            performance_monitor = PerformanceMonitor()
            await performance_monitor.start_monitoring()
            
            # Record test metrics
            for i in range(10):
                await performance_monitor.record_metric(
                    "test_response_time", float(i * 0.1), "seconds"
                )
                await performance_monitor.record_metric(
                    "test_cpu_usage", float(30 + i * 2), "percent"
                )
                await performance_monitor.record_metric(
                    "test_memory_usage", float(40 + i * 3), "percent"
                )
            
            # Wait for metrics processing
            await asyncio.sleep(2.0)
            
            # Get performance report
            performance_report = await performance_monitor.get_performance_report()
            
            # Get health status
            health_status = await performance_monitor.get_health_status()
            
            await performance_monitor.stop_monitoring()
            
            return {
                "status": "success",
                "metrics_recorded": 30,  # 10 iterations * 3 metrics
                "performance_report": performance_report,
                "health_status": health_status
            }
            
        except Exception as e:
            logger.error(f"Performance monitoring test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_concurrent_processing(self) -> Dict[str, Any]:
        """Test concurrent processing performance."""
        try:
            config = ConcurrencyConfig(
                max_concurrent_extractions=3,
                max_concurrent_searches=5,
                max_concurrent_crawls=4
            )
            
            concurrent_service = ConcurrentExtractionService(config)
            
            async with concurrent_service:
                # Submit test extraction tasks
                task_ids = []
                start_time = time.time()
                
                for company in self.test_companies[:5]:  # Test with 5 companies
                    try:
                        request = CompanyInformationRequest(
                            company_name=company,
                            extraction_mode=ExtractionMode.BASIC,
                            timeout_seconds=30
                        )
                        
                        task_id = await concurrent_service.extract_company_async(request)
                        task_ids.append(task_id)
                        
                    except Exception as e:
                        logger.warning(f"Failed to submit task for {company}: {e}")
                
                submission_time = time.time() - start_time
                
                # Wait for some tasks to complete (limited time)
                await asyncio.sleep(10.0)
                
                # Check task statuses
                completed_tasks = 0
                processing_tasks = 0
                failed_tasks = 0
                
                for task_id in task_ids:
                    try:
                        status = await concurrent_service.get_task_status(task_id)
                        if status["status"] == "completed":
                            completed_tasks += 1
                        elif status["status"] == "processing":
                            processing_tasks += 1
                        elif status["status"] == "failed":
                            failed_tasks += 1
                    except Exception as e:
                        logger.warning(f"Failed to get status for task {task_id}: {e}")
                        failed_tasks += 1
                
                # Get performance metrics
                performance_metrics = await concurrent_service.get_performance_metrics()
                
                return {
                    "status": "success",
                    "tasks_submitted": len(task_ids),
                    "submission_time": submission_time,
                    "task_statuses": {
                        "completed": completed_tasks,
                        "processing": processing_tasks,
                        "failed": failed_tasks
                    },
                    "performance_metrics": performance_metrics
                }
                
        except Exception as e:
            logger.error(f"Concurrent processing test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_api_performance(self) -> Dict[str, Any]:
        """Test API performance with caching."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Test health endpoint
                health_start = time.time()
                health_response = await client.get(f"{self.base_url}/api/v1/health")
                health_time = time.time() - health_start
                
                if health_response.status_code != 200:
                    return {
                        "status": "failed",
                        "error": f"Health check failed: {health_response.status_code}"
                    }
                
                # Test company health endpoint
                company_health_start = time.time()
                company_health_response = await client.get(f"{self.base_url}/api/v1/company/health")
                company_health_time = time.time() - company_health_start
                
                # Test single extraction (basic mode for faster response)
                extraction_times = []
                for company in self.test_companies[:3]:  # Test with 3 companies
                    try:
                        request_data = {
                            "company_name": company,
                            "extraction_mode": "basic",
                            "timeout_seconds": 30
                        }
                        
                        extraction_start = time.time()
                        extraction_response = await client.post(
                            f"{self.base_url}/api/v1/company/extract",
                            json=request_data,
                            timeout=45.0
                        )
                        extraction_time = time.time() - extraction_start
                        
                        if extraction_response.status_code == 200:
                            extraction_times.append(extraction_time)
                            logger.info(f"Extraction for {company} completed in {extraction_time:.2f}s")
                        else:
                            logger.warning(f"Extraction failed for {company}: {extraction_response.status_code}")
                            
                    except Exception as e:
                        logger.warning(f"Extraction request failed for {company}: {e}")
                
                return {
                    "status": "success",
                    "health_check_time": health_time,
                    "company_health_time": company_health_time,
                    "extraction_performance": {
                        "successful_extractions": len(extraction_times),
                        "avg_time": sum(extraction_times) / len(extraction_times) if extraction_times else 0,
                        "min_time": min(extraction_times) if extraction_times else 0,
                        "max_time": max(extraction_times) if extraction_times else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"API performance test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_batch_processing(self) -> Dict[str, Any]:
        """Test batch processing performance."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Test batch submission
                batch_request = {
                    "company_names": self.test_companies[:5],  # Test with 5 companies
                    "extraction_mode": "basic",
                    "priority": "normal",
                    "export_format": "json",
                    "timeout_seconds": 30
                }
                
                submission_start = time.time()
                submission_response = await client.post(
                    f"{self.base_url}/api/v1/company/batch/submit",
                    json=batch_request
                )
                submission_time = time.time() - submission_start
                
                if submission_response.status_code != 202:
                    logger.warning(f"Batch submission failed: {submission_response.status_code}")
                    return {
                        "status": "failed",
                        "error": f"Batch submission failed: {submission_response.status_code}"
                    }
                
                batch_data = submission_response.json()
                batch_id = batch_data["batch_id"]
                logger.info(f"Batch submitted: {batch_id}")
                
                # Monitor batch progress
                status_checks = []
                max_wait_time = 60.0  # Wait up to 60 seconds
                check_interval = 5.0
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    status_start = time.time()
                    status_response = await client.get(
                        f"{self.base_url}/api/v1/company/batch/{batch_id}/status"
                    )
                    status_check_time = time.time() - status_start
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status_checks.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": status_data["status"],
                            "progress": status_data["progress"],
                            "check_time": status_check_time
                        })
                        
                        logger.info(f"Batch status: {status_data['status']}")
                        
                        if status_data["status"] in ["completed", "partially_completed", "failed"]:
                            break
                    
                    await asyncio.sleep(check_interval)
                    elapsed_time += check_interval
                
                # Get batch statistics
                stats_response = await client.get(f"{self.base_url}/api/v1/company/batch/stats")
                batch_stats = stats_response.json() if stats_response.status_code == 200 else {}
                
                return {
                    "status": "success",
                    "batch_id": batch_id,
                    "submission_time": submission_time,
                    "companies_submitted": len(batch_request["company_names"]),
                    "status_checks": len(status_checks),
                    "final_status": status_checks[-1]["status"] if status_checks else "unknown",
                    "batch_stats": batch_stats
                }
                
        except Exception as e:
            logger.error(f"Batch processing test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def save_results(self, output_file: str = "performance_test_results.json"):
        """Save test results to file."""
        try:
            output_path = Path(__file__).parent / output_file
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            logger.info(f"Test results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def print_summary(self):
        """Print test results summary."""
        if not self.results:
            logger.info("No test results available")
            return
        
        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS SUMMARY")
        print("="*60)
        
        for test_name, result in self.results.items():
            if test_name == "summary":
                continue
                
            status = result.get("status", "unknown")
            print(f"\n{test_name.upper()}: {status.upper()}")
            
            if status == "success":
                # Print key metrics for each test
                if test_name == "caching":
                    read_avg = result["read_performance"]["avg_time"] * 1000
                    write_avg = result["write_performance"]["avg_time"] * 1000
                    print(f"  - Average read time: {read_avg:.2f}ms")
                    print(f"  - Average write time: {write_avg:.2f}ms")
                    
                elif test_name == "api_performance":
                    extraction_perf = result["extraction_performance"]
                    if extraction_perf["successful_extractions"] > 0:
                        print(f"  - Successful extractions: {extraction_perf['successful_extractions']}")
                        print(f"  - Average extraction time: {extraction_perf['avg_time']:.2f}s")
                    
                elif test_name == "concurrent_processing":
                    print(f"  - Tasks submitted: {result['tasks_submitted']}")
                    print(f"  - Tasks completed: {result['task_statuses']['completed']}")
                    
                elif test_name == "batch_processing":
                    print(f"  - Batch ID: {result['batch_id']}")
                    print(f"  - Companies submitted: {result['companies_submitted']}")
                    print(f"  - Final status: {result['final_status']}")
            
            elif status == "failed":
                print(f"  - Error: {result.get('error', 'Unknown error')}")
        
        if "summary" in self.results:
            summary = self.results["summary"]
            print(f"\nTOTAL TEST TIME: {summary['total_test_time']:.2f} seconds")
            print(f"TESTS COMPLETED: {summary['tests_completed']}")
        
        print("\n" + "="*60)


async def main():
    """Main test execution function."""
    # Check if Redis is available
    try:
        redis_client = redis.from_url("redis://localhost:6379/0")
        await redis_client.ping()
        await redis_client.aclose()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        logger.info("Some tests may be skipped or fail")
    
    # Run performance tests
    test_suite = PerformanceTestSuite()
    
    try:
        results = await test_suite.run_all_tests()
        
        # Print summary
        test_suite.print_summary()
        
        # Save results
        test_suite.save_results()
        
        logger.info("Performance testing completed successfully")
        
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())