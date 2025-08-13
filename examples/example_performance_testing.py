#!/usr/bin/env python3
"""
Production Performance Testing Example

This example demonstrates how to perform comprehensive performance testing
of the Company Information Extraction API, including load testing, response
time analysis, and resource utilization monitoring.

Usage:
    python examples/example_performance_testing.py
"""

import asyncio
import sys
import logging
import time
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
import psutil
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    response_times: List[float]
    start_time: datetime
    end_time: datetime
    errors: List[str]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def median_response_time(self) -> float:
        """Calculate median response time."""
        return statistics.median(self.response_times) if self.response_times else 0.0
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    @property
    def total_duration(self) -> float:
        """Calculate total test duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def requests_per_second(self) -> float:
        """Calculate requests per second."""
        return self.total_requests / self.total_duration if self.total_duration > 0 else 0.0


class PerformanceTester:
    """Production-ready performance testing client."""
    
    def __init__(self, base_url: str = API_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
    
    async def test_single_extraction_performance(
        self, 
        company_name: str = "Microsoft",
        extraction_mode: str = "standard",
        num_requests: int = 10
    ) -> PerformanceMetrics:
        """Test single company extraction performance."""
        logger.info(f"Testing single extraction performance: {num_requests} requests")
        
        metrics = PerformanceMetrics(
            test_name=f"Single Extraction ({extraction_mode})",
            total_requests=num_requests,
            successful_requests=0,
            failed_requests=0,
            response_times=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            errors=[]
        )
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        ) as client:
            
            for i in range(num_requests):
                start_time = time.time()
                
                try:
                    response = await client.post(
                        "/api/v1/company/extract",
                        json={
                            "company_name": company_name,
                            "extraction_mode": extraction_mode
                        }
                    )
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    metrics.response_times.append(response_time)
                    
                    if response.status_code == 200:
                        metrics.successful_requests += 1
                        logger.debug(f"Request {i+1}/{num_requests} successful: {response_time:.2f}s")
                    else:
                        metrics.failed_requests += 1
                        error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                        metrics.errors.append(error_msg)
                        logger.warning(f"Request {i+1}/{num_requests} failed: {error_msg}")
                
                except Exception as e:
                    end_time = time.time()
                    response_time = end_time - start_time
                    metrics.response_times.append(response_time)
                    metrics.failed_requests += 1
                    error_msg = f"Exception: {str(e)[:100]}"
                    metrics.errors.append(error_msg)
                    logger.error(f"Request {i+1}/{num_requests} exception: {error_msg}")
                
                # Brief pause between requests
                await asyncio.sleep(0.1)
        
        metrics.end_time = datetime.now()
        return metrics
    
    async def test_concurrent_extractions(
        self, 
        companies: List[str],
        extraction_mode: str = "basic",
        concurrent_requests: int = 5
    ) -> PerformanceMetrics:
        """Test concurrent company extractions."""
        logger.info(f"Testing concurrent extractions: {len(companies)} companies, {concurrent_requests} concurrent")
        
        metrics = PerformanceMetrics(
            test_name=f"Concurrent Extractions ({concurrent_requests} concurrent)",
            total_requests=len(companies),
            successful_requests=0,
            failed_requests=0,
            response_times=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            errors=[]
        )
        
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def extract_single_company(client: httpx.AsyncClient, company: str):
            """Extract data for a single company with rate limiting."""
            async with semaphore:
                start_time = time.time()
                
                try:
                    response = await client.post(
                        "/api/v1/company/extract",
                        json={
                            "company_name": company,
                            "extraction_mode": extraction_mode
                        }
                    )
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    return {
                        "company": company,
                        "success": response.status_code == 200,
                        "response_time": response_time,
                        "error": None if response.status_code == 200 else f"HTTP {response.status_code}"
                    }
                
                except Exception as e:
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    return {
                        "company": company,
                        "success": False,
                        "response_time": response_time,
                        "error": str(e)[:100]
                    }
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        ) as client:
            
            # Create tasks for all companies
            tasks = [extract_single_company(client, company) for company in companies]
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                metrics.failed_requests += 1
                metrics.errors.append(f"Task exception: {str(result)[:100]}")
                metrics.response_times.append(0.0)
            else:
                metrics.response_times.append(result["response_time"])
                if result["success"]:
                    metrics.successful_requests += 1
                else:
                    metrics.failed_requests += 1
                    if result["error"]:
                        metrics.errors.append(f"{result['company']}: {result['error']}")
        
        metrics.end_time = datetime.now()
        return metrics
    
    async def test_batch_processing_performance(
        self, 
        batch_sizes: List[int] = [5, 10, 20],
        extraction_mode: str = "standard"
    ) -> List[PerformanceMetrics]:
        """Test batch processing performance with different batch sizes."""
        logger.info(f"Testing batch processing performance: sizes {batch_sizes}")
        
        # Test companies
        test_companies = [
            "Microsoft", "Google", "Apple", "Amazon", "Meta",
            "Tesla", "Netflix", "Adobe", "Salesforce", "Oracle",
            "IBM", "Intel", "Nvidia", "AMD", "Cisco",
            "PayPal", "Square", "Zoom", "Slack", "Dropbox"
        ]
        
        results = []
        
        for batch_size in batch_sizes:
            companies = test_companies[:batch_size]
            metrics = await self._test_single_batch(companies, extraction_mode, batch_size)
            results.append(metrics)
        
        return results
    
    async def _test_single_batch(
        self, 
        companies: List[str], 
        extraction_mode: str, 
        batch_size: int
    ) -> PerformanceMetrics:
        """Test a single batch processing operation."""
        metrics = PerformanceMetrics(
            test_name=f"Batch Processing (size={batch_size})",
            total_requests=1,  # One batch request
            successful_requests=0,
            failed_requests=0,
            response_times=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            errors=[]
        )
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        ) as client:
            
            start_time = time.time()
            
            try:
                # Submit batch
                response = await client.post(
                    "/api/v1/company/batch/submit",
                    json={
                        "company_names": companies,
                        "extraction_mode": extraction_mode,
                        "priority": "normal"
                    }
                )
                
                if response.status_code != 200:
                    metrics.failed_requests = 1
                    metrics.errors.append(f"Batch submit failed: HTTP {response.status_code}")
                    metrics.response_times.append(time.time() - start_time)
                    metrics.end_time = datetime.now()
                    return metrics
                
                batch_id = response.json().get("batch_id")
                if not batch_id:
                    metrics.failed_requests = 1
                    metrics.errors.append("No batch_id returned")
                    metrics.response_times.append(time.time() - start_time)
                    metrics.end_time = datetime.now()
                    return metrics
                
                # Wait for completion
                while True:
                    status_response = await client.get(f"/api/v1/company/batch/{batch_id}/status")
                    
                    if status_response.status_code != 200:
                        metrics.failed_requests = 1
                        metrics.errors.append(f"Status check failed: HTTP {status_response.status_code}")
                        break
                    
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    
                    if status in ["completed", "failed", "cancelled"]:
                        if status == "completed":
                            metrics.successful_requests = 1
                        else:
                            metrics.failed_requests = 1
                            metrics.errors.append(f"Batch failed with status: {status}")
                        break
                    
                    await asyncio.sleep(5)  # Poll every 5 seconds
                
                end_time = time.time()
                metrics.response_times.append(end_time - start_time)
                
            except Exception as e:
                metrics.failed_requests = 1
                metrics.errors.append(f"Exception: {str(e)[:100]}")
                metrics.response_times.append(time.time() - start_time)
        
        metrics.end_time = datetime.now()
        return metrics
    
    def monitor_system_resources(self, duration: int = 60) -> Dict[str, Any]:
        """Monitor system resource usage during testing."""
        logger.info(f"Monitoring system resources for {duration} seconds")
        
        cpu_samples = []
        memory_samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            
            cpu_samples.append(cpu_percent)
            memory_samples.append(memory_info.percent)
            
            time.sleep(1)
        
        return {
            "duration": duration,
            "cpu_usage": {
                "average": statistics.mean(cpu_samples),
                "max": max(cpu_samples),
                "samples": cpu_samples
            },
            "memory_usage": {
                "average": statistics.mean(memory_samples),
                "max": max(memory_samples),
                "samples": memory_samples
            }
        }
    
    def print_metrics_report(self, metrics: PerformanceMetrics):
        """Print a detailed performance metrics report."""
        print(f"\n{'='*60}")
        print(f"Performance Test Report: {metrics.test_name}")
        print(f"{'='*60}")
        print(f"Test Duration: {metrics.total_duration:.2f} seconds")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful Requests: {metrics.successful_requests}")
        print(f"Failed Requests: {metrics.failed_requests}")
        print(f"Success Rate: {metrics.success_rate:.1f}%")
        print(f"Requests per Second: {metrics.requests_per_second:.2f}")
        
        if metrics.response_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Average: {metrics.average_response_time:.2f}s")
            print(f"  Median: {metrics.median_response_time:.2f}s")
            print(f"  95th Percentile: {metrics.p95_response_time:.2f}s")
            print(f"  Min: {min(metrics.response_times):.2f}s")
            print(f"  Max: {max(metrics.response_times):.2f}s")
        
        if metrics.errors:
            print(f"\nErrors ({len(metrics.errors)}):")
            for error in metrics.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(metrics.errors) > 5:
                print(f"  ... and {len(metrics.errors) - 5} more errors")
        
        print(f"{'='*60}")


async def run_performance_suite():
    """Run the complete performance testing suite."""
    tester = PerformanceTester()
    
    logger.info("Starting comprehensive performance testing suite")
    
    # Test 1: Single extraction performance
    logger.info("\n1. Testing single extraction performance...")
    single_metrics = await tester.test_single_extraction_performance(
        company_name="Microsoft",
        extraction_mode="basic",
        num_requests=20
    )
    tester.print_metrics_report(single_metrics)
    
    # Test 2: Concurrent extractions
    logger.info("\n2. Testing concurrent extractions...")
    test_companies = ["Microsoft", "Google", "Apple", "Amazon", "Tesla"]
    concurrent_metrics = await tester.test_concurrent_extractions(
        companies=test_companies,
        extraction_mode="basic",
        concurrent_requests=3
    )
    tester.print_metrics_report(concurrent_metrics)
    
    # Test 3: Batch processing performance
    logger.info("\n3. Testing batch processing performance...")
    batch_metrics_list = await tester.test_batch_processing_performance(
        batch_sizes=[3, 5, 8],
        extraction_mode="basic"
    )
    
    for metrics in batch_metrics_list:
        tester.print_metrics_report(metrics)
    
    # Test 4: Different extraction modes
    logger.info("\n4. Testing different extraction modes...")
    modes = ["basic", "standard"]  # Skip comprehensive for faster testing
    
    for mode in modes:
        logger.info(f"Testing {mode} mode...")
        mode_metrics = await tester.test_single_extraction_performance(
            company_name="OpenAI",
            extraction_mode=mode,
            num_requests=5
        )
        tester.print_metrics_report(mode_metrics)
    
    logger.info("\nPerformance testing suite completed!")


async def run_load_test():
    """Run a focused load test."""
    logger.info("Starting load test...")
    
    tester = PerformanceTester()
    
    # Load test configuration
    test_companies = ["Microsoft", "Google", "Apple", "Amazon"]
    concurrent_requests = 10
    
    logger.info(f"Load test: {len(test_companies)} companies, {concurrent_requests} concurrent requests")
    
    # Monitor resources during load test
    def monitor_resources():
        return tester.monitor_system_resources(duration=120)  # 2 minutes
    
    # Run load test and resource monitoring concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        resource_future = executor.submit(monitor_resources)
        
        # Run multiple rounds of concurrent extractions
        load_results = []
        for round_num in range(5):  # 5 rounds
            logger.info(f"Load test round {round_num + 1}/5")
            
            metrics = await tester.test_concurrent_extractions(
                companies=test_companies,
                extraction_mode="basic",
                concurrent_requests=concurrent_requests
            )
            load_results.append(metrics)
            
            await asyncio.sleep(10)  # Brief pause between rounds
        
        # Get resource monitoring results
        resource_stats = resource_future.result()
    
    # Print results
    logger.info("\nLoad Test Results:")
    for i, metrics in enumerate(load_results):
        print(f"\nRound {i + 1}:")
        tester.print_metrics_report(metrics)
    
    # Print resource usage
    print(f"\nSystem Resource Usage:")
    print(f"CPU Usage - Average: {resource_stats['cpu_usage']['average']:.1f}%, Max: {resource_stats['cpu_usage']['max']:.1f}%")
    print(f"Memory Usage - Average: {resource_stats['memory_usage']['average']:.1f}%, Max: {resource_stats['memory_usage']['max']:.1f}%")


async def main():
    """Main function to run performance tests."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "load":
            await run_load_test()
        elif test_type == "suite":
            await run_performance_suite()
        else:
            print("Usage: python example_performance_testing.py [load|suite]")
            sys.exit(1)
    else:
        # Default: run the full suite
        await run_performance_suite()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Performance testing interrupted by user")
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
        sys.exit(1)