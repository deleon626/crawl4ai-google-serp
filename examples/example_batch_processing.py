#!/usr/bin/env python3
"""
Production-Ready Batch Company Extraction Example

This example demonstrates how to use the Company Information Extraction API
for batch processing of multiple companies with different extraction modes,
priority levels, and monitoring capabilities.

Usage:
    python examples/example_batch_processing.py
"""

import asyncio
import sys
import logging
from typing import List, Dict, Any, Optional
import httpx
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 300  # 5 minutes


class BatchCompanyExtractor:
    """Production-ready batch company extraction client."""
    
    def __init__(self, base_url: str = API_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Initialize async HTTP client."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = await self.client.get("/api/v1/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def submit_batch(
        self, 
        companies: List[str],
        extraction_mode: str = "standard",
        priority: str = "normal",
        **kwargs
    ) -> Optional[str]:
        """Submit batch extraction request."""
        request_data = {
            "company_names": companies,
            "extraction_mode": extraction_mode,
            "priority": priority,
            **kwargs
        }
        
        try:
            logger.info(f"Submitting batch request for {len(companies)} companies")
            response = await self.client.post(
                "/api/v1/company/batch/submit",
                json=request_data
            )
            response.raise_for_status()
            
            batch_data = response.json()
            batch_id = batch_data.get("batch_id")
            logger.info(f"Batch submitted successfully: {batch_id}")
            return batch_id
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error submitting batch: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error submitting batch: {e}")
            return None
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch processing status."""
        try:
            response = await self.client.get(f"/api/v1/company/batch/{batch_id}/status")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting status: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            return None
    
    async def get_batch_results(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch processing results."""
        try:
            response = await self.client.get(f"/api/v1/company/batch/{batch_id}/results")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting results: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting batch results: {e}")
            return None
    
    async def wait_for_completion(
        self, 
        batch_id: str, 
        polling_interval: int = 10,
        max_wait_time: int = 1800  # 30 minutes
    ) -> Optional[Dict[str, Any]]:
        """Wait for batch processing to complete."""
        start_time = time.time()
        
        logger.info(f"Waiting for batch {batch_id} to complete...")
        
        while time.time() - start_time < max_wait_time:
            status_data = await self.get_batch_status(batch_id)
            
            if not status_data:
                logger.error("Failed to get batch status")
                await asyncio.sleep(polling_interval)
                continue
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", {})
            
            logger.info(
                f"Batch {batch_id} status: {status} | "
                f"Progress: {progress.get('completed', 0)}/{progress.get('total', 0)}"
            )
            
            if status in ["completed", "failed", "cancelled"]:
                if status == "completed":
                    logger.info(f"Batch {batch_id} completed successfully")
                    return await self.get_batch_results(batch_id)
                else:
                    logger.error(f"Batch {batch_id} finished with status: {status}")
                    return status_data
            
            await asyncio.sleep(polling_interval)
        
        logger.warning(f"Batch {batch_id} did not complete within {max_wait_time} seconds")
        return None


async def example_basic_batch():
    """Example 1: Basic batch processing with standard mode."""
    companies = [
        "OpenAI",
        "Microsoft",
        "Google",
        "Apple",
        "Amazon"
    ]
    
    async with BatchCompanyExtractor() as extractor:
        # Check API health
        if not await extractor.health_check():
            logger.error("API health check failed")
            return
        
        # Submit batch
        batch_id = await extractor.submit_batch(
            companies=companies,
            extraction_mode="standard",
            priority="normal"
        )
        
        if not batch_id:
            logger.error("Failed to submit batch")
            return
        
        # Wait for completion and get results
        results = await extractor.wait_for_completion(batch_id)
        
        if results:
            logger.info("Batch processing completed successfully")
            extracted_data = results.get("results", [])
            
            for company_data in extracted_data:
                company_name = company_data.get("company_name", "Unknown")
                success = company_data.get("success", False)
                logger.info(f"Company: {company_name}, Success: {success}")
        else:
            logger.error("Batch processing failed or timed out")


async def example_priority_batch():
    """Example 2: High-priority batch with comprehensive extraction."""
    tech_companies = [
        "Tesla",
        "SpaceX",
        "Stripe",
        "Databricks",
        "Anthropic"
    ]
    
    async with BatchCompanyExtractor() as extractor:
        if not await extractor.health_check():
            logger.error("API health check failed")
            return
        
        # Submit high-priority comprehensive batch
        batch_id = await extractor.submit_batch(
            companies=tech_companies,
            extraction_mode="comprehensive",
            priority="high",
            include_financial_data=True,
            include_contact_info=True,
            max_retries=3
        )
        
        if not batch_id:
            logger.error("Failed to submit priority batch")
            return
        
        # Monitor with shorter polling interval for high priority
        results = await extractor.wait_for_completion(
            batch_id, 
            polling_interval=5,  # More frequent polling
            max_wait_time=2400   # 40 minutes for comprehensive mode
        )
        
        if results:
            logger.info("Priority batch completed successfully")
            process_comprehensive_results(results)
        else:
            logger.error("Priority batch failed or timed out")


async def example_mixed_mode_batches():
    """Example 3: Multiple batches with different extraction modes."""
    batches = [
        {
            "name": "Quick Validation",
            "companies": ["Salesforce", "HubSpot", "Pipedrive"],
            "mode": "basic",
            "priority": "normal"
        },
        {
            "name": "Sales Prospects",
            "companies": ["Zoom", "Slack", "Monday.com"],
            "mode": "contact_focused",
            "priority": "high"
        },
        {
            "name": "Investment Research",
            "companies": ["Palantir", "Snowflake", "CrowdStrike"],
            "mode": "financial_focused",
            "priority": "high"
        }
    ]
    
    async with BatchCompanyExtractor() as extractor:
        if not await extractor.health_check():
            logger.error("API health check failed")
            return
        
        # Submit all batches concurrently
        batch_tasks = []
        for batch_config in batches:
            task = submit_and_monitor_batch(extractor, batch_config)
            batch_tasks.append(task)
        
        # Wait for all batches to complete
        results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            batch_name = batches[i]["name"]
            if isinstance(result, Exception):
                logger.error(f"Batch '{batch_name}' failed with exception: {result}")
            elif result:
                logger.info(f"Batch '{batch_name}' completed successfully")
                log_batch_summary(result, batch_name)
            else:
                logger.warning(f"Batch '{batch_name}' returned no results")


async def submit_and_monitor_batch(extractor: BatchCompanyExtractor, batch_config: Dict[str, Any]):
    """Helper function to submit and monitor a single batch."""
    batch_id = await extractor.submit_batch(
        companies=batch_config["companies"],
        extraction_mode=batch_config["mode"],
        priority=batch_config["priority"]
    )
    
    if not batch_id:
        logger.error(f"Failed to submit batch: {batch_config['name']}")
        return None
    
    return await extractor.wait_for_completion(batch_id)


def process_comprehensive_results(results: Dict[str, Any]):
    """Process comprehensive extraction results."""
    extracted_data = results.get("results", [])
    batch_metadata = results.get("metadata", {})
    
    logger.info(f"Batch metadata: {batch_metadata}")
    
    for company_data in extracted_data:
        if not company_data.get("success", False):
            continue
            
        data = company_data.get("data", {})
        company_name = data.get("company_name", "Unknown")
        industry = data.get("industry", "Unknown")
        
        # Financial data
        financial_data = data.get("financial_data", {})
        revenue = financial_data.get("revenue", "Not available")
        valuation = financial_data.get("valuation", "Not available")
        
        # Contact information
        contact_info = data.get("contact_info", {})
        headquarters = contact_info.get("headquarters", "Unknown")
        website = contact_info.get("website", "Unknown")
        
        logger.info(f"""
Company: {company_name}
Industry: {industry}
Revenue: {revenue}
Valuation: {valuation}
Headquarters: {headquarters}
Website: {website}
        """)


def log_batch_summary(results: Dict[str, Any], batch_name: str):
    """Log a summary of batch results."""
    extracted_data = results.get("results", [])
    successful = sum(1 for item in extracted_data if item.get("success", False))
    total = len(extracted_data)
    
    logger.info(f"""
Batch Summary - {batch_name}:
- Total companies: {total}
- Successful extractions: {successful}
- Success rate: {(successful/total*100):.1f}%
    """)


async def example_error_handling():
    """Example 4: Error handling and retry logic."""
    companies_with_issues = [
        "ValidCompany",  # This should work
        "NonExistentCompany12345",  # This might fail
        "Microsoft",  # This should work
    ]
    
    async with BatchCompanyExtractor() as extractor:
        if not await extractor.health_check():
            logger.error("API health check failed")
            return
        
        # Submit batch with retry configuration
        batch_id = await extractor.submit_batch(
            companies=companies_with_issues,
            extraction_mode="basic",
            priority="normal",
            max_retries=2,
            timeout_per_company=60
        )
        
        if not batch_id:
            logger.error("Failed to submit batch with potential errors")
            return
        
        results = await extractor.wait_for_completion(batch_id)
        
        if results:
            extracted_data = results.get("results", [])
            
            for company_data in extracted_data:
                company_name = company_data.get("company_name", "Unknown")
                success = company_data.get("success", False)
                error = company_data.get("error")
                
                if success:
                    logger.info(f"✅ {company_name}: Successfully extracted")
                else:
                    logger.warning(f"❌ {company_name}: Failed - {error}")


async def main():
    """Run all batch processing examples."""
    logger.info("Starting batch processing examples...")
    logger.info("=" * 60)
    
    try:
        logger.info("Running Example 1: Basic batch processing")
        await example_basic_batch()
        logger.info("=" * 60)
        
        logger.info("Running Example 2: High-priority comprehensive batch")
        await example_priority_batch()
        logger.info("=" * 60)
        
        logger.info("Running Example 3: Multiple batches with different modes")
        await example_mixed_mode_batches()
        logger.info("=" * 60)
        
        logger.info("Running Example 4: Error handling and retry logic")
        await example_error_handling()
        logger.info("=" * 60)
        
        logger.info("All examples completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())