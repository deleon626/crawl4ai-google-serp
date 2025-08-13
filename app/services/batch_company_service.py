"""Batch processing service for multi-company extraction with intelligent scheduling and progress tracking."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from app.models.company import (
    CompanyInformationRequest, CompanyExtractionResponse, 
    CompanyInformation, ExtractionMetadata, ExtractionError, ExtractionMode
)
from app.services.concurrent_extraction import ConcurrentExtractionService, ConcurrencyConfig
from app.utils.caching import get_cache_service, CacheKeyGenerator
from app.utils.resource_manager import get_resource_manager

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Batch processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_COMPLETED = "partially_completed"


class BatchPriority(str, Enum):
    """Batch processing priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BatchProgressUpdate:
    """Batch processing progress update."""
    batch_id: str
    total_companies: int
    completed: int
    failed: int
    processing: int
    queued: int
    success_rate: float
    avg_processing_time: float
    estimated_completion: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchRequest:
    """Batch company extraction request."""
    batch_id: str
    company_names: List[str]
    extraction_mode: ExtractionMode = ExtractionMode.STANDARD
    priority: BatchPriority = BatchPriority.NORMAL
    country: str = "US"
    language: str = "en"
    domain_hints: Optional[Dict[str, str]] = None  # company_name -> domain mapping
    max_concurrent: int = 5
    timeout_seconds: int = 300
    include_failed_results: bool = True
    export_format: str = "json"  # json, csv, excel
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        # Remove duplicates while preserving order
        seen = set()
        unique_companies = []
        for company in self.company_names:
            if company.lower().strip() not in seen:
                seen.add(company.lower().strip())
                unique_companies.append(company.strip())
        self.company_names = unique_companies


@dataclass
class BatchResult:
    """Batch processing result."""
    batch_id: str
    status: BatchStatus
    total_companies: int
    successful_extractions: int
    failed_extractions: int
    results: Dict[str, CompanyExtractionResponse]
    processing_time: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    export_path: Optional[str] = None
    summary_stats: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)


class BatchScheduler:
    """Intelligent batch scheduling and priority management."""
    
    def __init__(self, max_concurrent_batches: int = 3):
        """Initialize batch scheduler."""
        self.max_concurrent_batches = max_concurrent_batches
        self._batch_queue = asyncio.PriorityQueue()
        self._active_batches: Dict[str, BatchRequest] = {}
        self._batch_stats = {
            "total_batches": 0,
            "completed_batches": 0,
            "failed_batches": 0,
            "avg_batch_time": 0.0
        }
        self._lock = asyncio.Lock()
        
        logger.info(f"BatchScheduler initialized with max_concurrent: {max_concurrent_batches}")
    
    async def schedule_batch(self, batch_request: BatchRequest) -> bool:
        """Schedule batch for processing."""
        try:
            # Calculate priority score (lower number = higher priority)
            priority_scores = {
                BatchPriority.URGENT: 1,
                BatchPriority.HIGH: 2,
                BatchPriority.NORMAL: 3,
                BatchPriority.LOW: 4
            }
            
            priority_score = priority_scores.get(batch_request.priority, 3)
            
            # Add timestamp as tiebreaker (earlier = higher priority)
            timestamp_score = batch_request.created_at.timestamp()
            
            await self._batch_queue.put((priority_score, timestamp_score, batch_request))
            
            async with self._lock:
                self._batch_stats["total_batches"] += 1
            
            logger.info(f"Batch scheduled: {batch_request.batch_id} "
                       f"(priority: {batch_request.priority}, companies: {len(batch_request.company_names)})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling batch {batch_request.batch_id}: {e}")
            return False
    
    async def get_next_batch(self, timeout: Optional[float] = None) -> Optional[BatchRequest]:
        """Get next batch to process."""
        try:
            # Check if we can process another batch
            async with self._lock:
                if len(self._active_batches) >= self.max_concurrent_batches:
                    return None
            
            # Get next batch from queue
            _, _, batch_request = await asyncio.wait_for(
                self._batch_queue.get(), 
                timeout=timeout
            )
            
            async with self._lock:
                self._active_batches[batch_request.batch_id] = batch_request
            
            logger.debug(f"Batch dequeued for processing: {batch_request.batch_id}")
            return batch_request
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting next batch: {e}")
            return None
    
    async def complete_batch(self, batch_id: str, success: bool, processing_time: float):
        """Mark batch as completed."""
        async with self._lock:
            if batch_id in self._active_batches:
                del self._active_batches[batch_id]
                
                if success:
                    self._batch_stats["completed_batches"] += 1
                else:
                    self._batch_stats["failed_batches"] += 1
                
                # Update average processing time
                total_completed = self._batch_stats["completed_batches"] + self._batch_stats["failed_batches"]
                if total_completed > 0:
                    current_avg = self._batch_stats["avg_batch_time"]
                    self._batch_stats["avg_batch_time"] = (
                        (current_avg * (total_completed - 1) + processing_time) / total_completed
                    )
        
        logger.info(f"Batch completed: {batch_id} (success: {success}, time: {processing_time:.2f}s)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "queue_size": self._batch_queue.qsize(),
            "active_batches": len(self._active_batches),
            "max_concurrent": self.max_concurrent_batches,
            "total_batches": self._batch_stats["total_batches"],
            "completed_batches": self._batch_stats["completed_batches"],
            "failed_batches": self._batch_stats["failed_batches"],
            "avg_batch_time": round(self._batch_stats["avg_batch_time"], 2)
        }


class BatchExporter:
    """Export batch results to various formats."""
    
    def __init__(self, export_dir: Optional[Path] = None):
        """Initialize batch exporter."""
        self.export_dir = export_dir or Path("exports")
        self.export_dir.mkdir(exist_ok=True)
        
        logger.info(f"BatchExporter initialized with export_dir: {self.export_dir}")
    
    async def export_results(
        self, 
        batch_result: BatchResult, 
        format: str = "json"
    ) -> str:
        """Export batch results to specified format."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_{batch_result.batch_id}_{timestamp}.{format}"
            export_path = self.export_dir / filename
            
            if format.lower() == "json":
                await self._export_json(batch_result, export_path)
            elif format.lower() == "csv":
                await self._export_csv(batch_result, export_path)
            elif format.lower() == "excel":
                await self._export_excel(batch_result, export_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Batch results exported: {export_path}")
            return str(export_path)
            
        except Exception as e:
            logger.error(f"Error exporting batch results: {e}")
            raise
    
    async def _export_json(self, batch_result: BatchResult, export_path: Path):
        """Export to JSON format."""
        export_data = {
            "batch_info": {
                "batch_id": batch_result.batch_id,
                "status": batch_result.status.value,
                "total_companies": batch_result.total_companies,
                "successful_extractions": batch_result.successful_extractions,
                "failed_extractions": batch_result.failed_extractions,
                "processing_time": batch_result.processing_time,
                "created_at": batch_result.created_at.isoformat(),
                "completed_at": batch_result.completed_at.isoformat() if batch_result.completed_at else None
            },
            "summary_stats": batch_result.summary_stats or {},
            "companies": []
        }
        
        # Add company results
        for company_name, response in batch_result.results.items():
            company_data = {
                "company_name": company_name,
                "success": response.success,
                "processing_time": response.processing_time,
                "company_information": response.company_information.dict() if response.company_information else None,
                "extraction_metadata": response.extraction_metadata.dict() if response.extraction_metadata else None,
                "errors": [error.dict() for error in response.errors],
                "warnings": response.warnings
            }
            export_data["companies"].append(company_data)
        
        # Write to file
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    async def _export_csv(self, batch_result: BatchResult, export_path: Path):
        """Export to CSV format."""
        import csv
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "Company Name", "Success", "Processing Time (s)", 
                "Basic Info - Description", "Basic Info - Industry", "Basic Info - Founded Year",
                "Basic Info - Employee Count", "Contact - Email", "Contact - Phone",
                "Contact - Address", "Social Media Count", "Key Personnel Count",
                "Confidence Score", "Errors", "Warnings"
            ])
            
            # Write data rows
            for company_name, response in batch_result.results.items():
                company_info = response.company_information
                
                if company_info:
                    basic = company_info.basic_info
                    contact = company_info.contact
                    
                    row = [
                        company_name,
                        response.success,
                        response.processing_time,
                        basic.description or "",
                        basic.industry or "",
                        basic.founded_year or "",
                        basic.employee_count or "",
                        contact.email if contact else "",
                        contact.phone if contact else "",
                        contact.address if contact else "",
                        len(company_info.social_media),
                        len(company_info.key_personnel),
                        company_info.confidence_score,
                        "; ".join([error.error_message for error in response.errors]),
                        "; ".join(response.warnings)
                    ]
                else:
                    row = [
                        company_name, response.success, response.processing_time,
                        "", "", "", "", "", "", "", 0, 0, 0.0,
                        "; ".join([error.error_message for error in response.errors]),
                        "; ".join(response.warnings)
                    ]
                
                writer.writerow(row)
    
    async def _export_excel(self, batch_result: BatchResult, export_path: Path):
        """Export to Excel format."""
        try:
            import pandas as pd
            
            # Prepare data for DataFrame
            data = []
            
            for company_name, response in batch_result.results.items():
                company_info = response.company_information
                
                if company_info:
                    basic = company_info.basic_info
                    contact = company_info.contact
                    
                    row_data = {
                        "Company Name": company_name,
                        "Success": response.success,
                        "Processing Time (s)": response.processing_time,
                        "Description": basic.description or "",
                        "Industry": basic.industry or "",
                        "Founded Year": basic.founded_year,
                        "Employee Count": basic.employee_count,
                        "Company Size": basic.company_size or "",
                        "Email": contact.email if contact else "",
                        "Phone": contact.phone if contact else "",
                        "Address": contact.address if contact else "",
                        "City": contact.city if contact else "",
                        "Country": contact.country if contact else "",
                        "Social Media Count": len(company_info.social_media),
                        "Key Personnel Count": len(company_info.key_personnel),
                        "Confidence Score": company_info.confidence_score,
                        "Data Quality Score": company_info.data_quality_score,
                        "Completeness Score": company_info.completeness_score,
                        "Errors": "; ".join([error.error_message for error in response.errors]),
                        "Warnings": "; ".join(response.warnings)
                    }
                else:
                    row_data = {
                        "Company Name": company_name,
                        "Success": response.success,
                        "Processing Time (s)": response.processing_time,
                        "Description": "",
                        "Industry": "",
                        "Founded Year": None,
                        "Employee Count": None,
                        "Company Size": "",
                        "Email": "",
                        "Phone": "",
                        "Address": "",
                        "City": "",
                        "Country": "",
                        "Social Media Count": 0,
                        "Key Personnel Count": 0,
                        "Confidence Score": 0.0,
                        "Data Quality Score": 0.0,
                        "Completeness Score": 0.0,
                        "Errors": "; ".join([error.error_message for error in response.errors]),
                        "Warnings": "; ".join(response.warnings)
                    }
                
                data.append(row_data)
            
            # Create DataFrame and export
            df = pd.DataFrame(data)
            df.to_excel(export_path, index=False, engine='openpyxl')
            
        except ImportError:
            # Fallback to CSV if pandas/openpyxl not available
            csv_path = export_path.with_suffix('.csv')
            await self._export_csv(batch_result, csv_path)
            logger.warning(f"Excel export unavailable, exported to CSV: {csv_path}")
            return str(csv_path)


class BatchCompanyService:
    """High-level batch company extraction service."""
    
    def __init__(
        self, 
        concurrency_config: Optional[ConcurrencyConfig] = None,
        max_concurrent_batches: int = 3,
        export_dir: Optional[Path] = None
    ):
        """Initialize batch company service."""
        self.concurrency_config = concurrency_config or ConcurrencyConfig(
            max_concurrent_extractions=8,
            batch_size=20
        )
        
        # Components
        self.scheduler = BatchScheduler(max_concurrent_batches)
        self.exporter = BatchExporter(export_dir)
        
        # Services
        self._concurrent_service: Optional[ConcurrentExtractionService] = None
        self._cache_service = None
        self._resource_manager = None
        
        # Batch storage and tracking
        self._active_batches: Dict[str, BatchRequest] = {}
        self._completed_batches: Dict[str, BatchResult] = {}
        self._batch_progress: Dict[str, BatchProgressUpdate] = {}
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Progress callbacks
        self._progress_callbacks: Dict[str, Callable[[BatchProgressUpdate], Awaitable[None]]] = {}
        
        logger.info(f"BatchCompanyService initialized with max_concurrent_batches: {max_concurrent_batches}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start batch processing service."""
        logger.info("Starting batch company service")
        
        # Initialize services
        self._concurrent_service = ConcurrentExtractionService(self.concurrency_config)
        await self._concurrent_service.start()
        
        self._cache_service = await get_cache_service()
        self._resource_manager = await get_resource_manager()
        
        # Start batch processing workers
        for i in range(self.scheduler.max_concurrent_batches):
            worker = asyncio.create_task(self._batch_worker(f"batch-worker-{i}"))
            self._workers.append(worker)
        
        logger.info(f"Started {len(self._workers)} batch processing workers")
    
    async def stop(self):
        """Stop batch processing service."""
        logger.info("Stopping batch company service")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for workers to complete
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
        
        # Stop services
        if self._concurrent_service:
            await self._concurrent_service.stop()
        
        logger.info("Batch company service stopped")
    
    async def submit_batch(
        self, 
        company_names: List[str],
        extraction_mode: ExtractionMode = ExtractionMode.STANDARD,
        priority: BatchPriority = BatchPriority.NORMAL,
        **kwargs
    ) -> str:
        """Submit batch for processing."""
        batch_request = BatchRequest(
            batch_id="",  # Will be generated in __post_init__
            company_names=company_names,
            extraction_mode=extraction_mode,
            priority=priority,
            **kwargs
        )
        
        # Check for cached results
        if self._cache_service:
            cached_count = await self._check_cached_companies(batch_request)
            if cached_count > 0:
                logger.info(f"Found {cached_count}/{len(company_names)} companies in cache")
        
        # Schedule batch
        success = await self.scheduler.schedule_batch(batch_request)
        
        if success:
            logger.info(f"Batch submitted: {batch_request.batch_id} "
                       f"({len(company_names)} companies, priority: {priority})")
            return batch_request.batch_id
        else:
            raise Exception("Failed to schedule batch processing")
    
    async def _check_cached_companies(self, batch_request: BatchRequest) -> int:
        """Check how many companies are already cached."""
        cached_count = 0
        
        for company_name in batch_request.company_names:
            domain = batch_request.domain_hints.get(company_name) if batch_request.domain_hints else None
            cached_result = await self._cache_service.get_company_info(
                company_name, domain, batch_request.extraction_mode.value
            )
            
            if cached_result:
                cached_count += 1
        
        return cached_count
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a batch."""
        # Check if completed
        if batch_id in self._completed_batches:
            result = self._completed_batches[batch_id]
            return {
                "batch_id": batch_id,
                "status": result.status.value,
                "progress": {
                    "total": result.total_companies,
                    "completed": result.successful_extractions,
                    "failed": result.failed_extractions,
                    "success_rate": (result.successful_extractions / result.total_companies * 100) if result.total_companies > 0 else 0
                },
                "processing_time": result.processing_time,
                "created_at": result.created_at.isoformat(),
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "export_path": result.export_path
            }
        
        # Check if active
        if batch_id in self._active_batches:
            progress = self._batch_progress.get(batch_id)
            if progress:
                return {
                    "batch_id": batch_id,
                    "status": BatchStatus.PROCESSING.value,
                    "progress": {
                        "total": progress.total_companies,
                        "completed": progress.completed,
                        "failed": progress.failed,
                        "processing": progress.processing,
                        "queued": progress.queued,
                        "success_rate": progress.success_rate,
                        "avg_processing_time": progress.avg_processing_time
                    },
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None,
                    "last_update": progress.timestamp.isoformat()
                }
            else:
                return {
                    "batch_id": batch_id,
                    "status": BatchStatus.PROCESSING.value,
                    "progress": {"message": "Processing started, no progress data yet"}
                }
        
        # Must be queued
        return {
            "batch_id": batch_id,
            "status": BatchStatus.QUEUED.value,
            "progress": {"message": "Waiting in queue"}
        }
    
    async def get_batch_result(self, batch_id: str) -> Optional[BatchResult]:
        """Get completed batch result."""
        return self._completed_batches.get(batch_id)
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch (if not yet started processing)."""
        # TODO: Implement batch cancellation logic
        logger.info(f"Batch cancellation requested: {batch_id}")
        return False  # Not implemented yet
    
    async def _batch_worker(self, worker_id: str):
        """Batch processing worker."""
        logger.info(f"Batch worker {worker_id} started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get next batch to process
                batch_request = await self.scheduler.get_next_batch(timeout=5.0)
                
                if batch_request is None:
                    continue  # No batch available, try again
                
                logger.info(f"Worker {worker_id} processing batch: {batch_request.batch_id}")
                
                # Process the batch
                start_time = time.time()
                batch_result = await self._process_batch(batch_request)
                processing_time = time.time() - start_time
                
                # Complete batch
                await self.scheduler.complete_batch(
                    batch_request.batch_id, 
                    batch_result.status == BatchStatus.COMPLETED,
                    processing_time
                )
                
                # Store result
                batch_result.processing_time = processing_time
                batch_result.completed_at = datetime.utcnow()
                self._completed_batches[batch_request.batch_id] = batch_result
                
                # Remove from active batches
                if batch_request.batch_id in self._active_batches:
                    del self._active_batches[batch_request.batch_id]
                
                # Export results if requested
                if batch_request.export_format:
                    try:
                        export_path = await self.exporter.export_results(
                            batch_result, batch_request.export_format
                        )
                        batch_result.export_path = export_path
                    except Exception as e:
                        logger.error(f"Failed to export batch results: {e}")
                        batch_result.errors.append(f"Export failed: {str(e)}")
                
                logger.info(f"Worker {worker_id} completed batch: {batch_request.batch_id} "
                           f"(status: {batch_result.status.value}, time: {processing_time:.2f}s)")
                
            except asyncio.CancelledError:
                logger.info(f"Batch worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Batch worker {worker_id} error: {e}")
                await asyncio.sleep(5.0)  # Brief pause on error
        
        logger.info(f"Batch worker {worker_id} stopped")
    
    async def _process_batch(self, batch_request: BatchRequest) -> BatchResult:
        """Process a single batch."""
        batch_id = batch_request.batch_id
        company_names = batch_request.company_names
        
        logger.info(f"Processing batch {batch_id} with {len(company_names)} companies")
        
        # Initialize batch tracking
        self._active_batches[batch_id] = batch_request
        results: Dict[str, CompanyExtractionResponse] = {}
        successful_count = 0
        failed_count = 0
        
        try:
            # Submit all extraction tasks
            task_ids = []
            
            for company_name in company_names:
                try:
                    # Create individual request
                    domain = batch_request.domain_hints.get(company_name) if batch_request.domain_hints else None
                    
                    company_request = CompanyInformationRequest(
                        company_name=company_name,
                        domain=domain,
                        extraction_mode=batch_request.extraction_mode,
                        country=batch_request.country,
                        language=batch_request.language,
                        timeout_seconds=batch_request.timeout_seconds
                    )
                    
                    # Submit for async processing
                    task_id = await self._concurrent_service.extract_company_async(
                        company_request,
                        priority=2.0 if batch_request.priority == BatchPriority.HIGH else 1.0
                    )
                    
                    task_ids.append((company_name, task_id))
                    
                except Exception as e:
                    logger.error(f"Failed to submit task for {company_name}: {e}")
                    # Create failed response
                    failed_response = CompanyExtractionResponse(
                        request_id=f"failed_{company_name}",
                        company_name=company_name,
                        success=False,
                        company_information=None,
                        extraction_metadata=None,
                        errors=[ExtractionError(
                            error_type="SubmissionError",
                            error_message=f"Failed to submit extraction task: {str(e)}"
                        )],
                        warnings=[],
                        processing_time=0.0
                    )
                    results[company_name] = failed_response
                    failed_count += 1
            
            logger.info(f"Submitted {len(task_ids)} extraction tasks for batch {batch_id}")
            
            # Monitor progress and collect results
            remaining_tasks = dict(task_ids)
            processed_companies = set()
            
            # Progress tracking
            total_companies = len(company_names)
            start_time = time.time()
            
            while remaining_tasks:
                # Check completed tasks
                completed_tasks = []
                
                for company_name, task_id in remaining_tasks.items():
                    try:
                        task_status = await self._concurrent_service.get_task_status(task_id)
                        
                        if task_status["status"] == "completed":
                            results[company_name] = task_status["result"]
                            if task_status["result"].success:
                                successful_count += 1
                            else:
                                failed_count += 1
                            completed_tasks.append(company_name)
                            processed_companies.add(company_name)
                            
                        elif task_status["status"] == "failed":
                            # Create failed response
                            failed_response = CompanyExtractionResponse(
                                request_id=task_id,
                                company_name=company_name,
                                success=False,
                                company_information=None,
                                extraction_metadata=None,
                                errors=[ExtractionError(
                                    error_type="ProcessingError",
                                    error_message=task_status.get("error", "Unknown processing error")
                                )],
                                warnings=[],
                                processing_time=0.0
                            )
                            results[company_name] = failed_response
                            failed_count += 1
                            completed_tasks.append(company_name)
                            processed_companies.add(company_name)
                            
                    except Exception as e:
                        logger.error(f"Error checking task status for {company_name}: {e}")
                
                # Remove completed tasks
                for company_name in completed_tasks:
                    del remaining_tasks[company_name]
                
                # Update progress
                completed_count = successful_count + failed_count
                processing_count = len([t for t in remaining_tasks.values() 
                                      if await self._get_task_processing_status(t) == "processing"])
                queued_count = len(remaining_tasks) - processing_count
                
                # Calculate metrics
                elapsed_time = time.time() - start_time
                success_rate = (successful_count / max(1, completed_count)) * 100
                avg_processing_time = elapsed_time / max(1, completed_count)
                
                # Estimate completion time
                estimated_completion = None
                if completed_count > 0 and remaining_tasks:
                    remaining_time = avg_processing_time * len(remaining_tasks)
                    estimated_completion = datetime.utcnow() + timedelta(seconds=remaining_time)
                
                # Create progress update
                progress_update = BatchProgressUpdate(
                    batch_id=batch_id,
                    total_companies=total_companies,
                    completed=completed_count,
                    failed=failed_count,
                    processing=processing_count,
                    queued=queued_count,
                    success_rate=success_rate,
                    avg_processing_time=avg_processing_time,
                    estimated_completion=estimated_completion
                )
                
                self._batch_progress[batch_id] = progress_update
                
                # Call progress callback if registered
                if batch_id in self._progress_callbacks:
                    try:
                        await self._progress_callbacks[batch_id](progress_update)
                    except Exception as e:
                        logger.error(f"Progress callback error for batch {batch_id}: {e}")
                
                if remaining_tasks:
                    await asyncio.sleep(2.0)  # Check every 2 seconds
            
            # Determine final status
            if successful_count == total_companies:
                final_status = BatchStatus.COMPLETED
            elif successful_count > 0:
                final_status = BatchStatus.PARTIALLY_COMPLETED
            else:
                final_status = BatchStatus.FAILED
            
            # Calculate summary statistics
            summary_stats = self._calculate_summary_stats(results)
            
            logger.info(f"Batch {batch_id} processing completed: {successful_count} successful, "
                       f"{failed_count} failed, status: {final_status.value}")
            
            return BatchResult(
                batch_id=batch_id,
                status=final_status,
                total_companies=total_companies,
                successful_extractions=successful_count,
                failed_extractions=failed_count,
                results=results,
                processing_time=0.0,  # Will be set by caller
                created_at=batch_request.created_at,
                summary_stats=summary_stats
            )
            
        except Exception as e:
            logger.error(f"Batch processing error for {batch_id}: {e}")
            
            return BatchResult(
                batch_id=batch_id,
                status=BatchStatus.FAILED,
                total_companies=len(company_names),
                successful_extractions=successful_count,
                failed_extractions=failed_count,
                results=results,
                processing_time=0.0,
                created_at=batch_request.created_at,
                errors=[f"Batch processing failed: {str(e)}"]
            )
    
    async def _get_task_processing_status(self, task_id: str) -> str:
        """Get simplified task status."""
        try:
            status = await self._concurrent_service.get_task_status(task_id)
            return status["status"]
        except Exception:
            return "unknown"
    
    def _calculate_summary_stats(self, results: Dict[str, CompanyExtractionResponse]) -> Dict[str, Any]:
        """Calculate summary statistics for batch results."""
        if not results:
            return {}
        
        successful_results = [r for r in results.values() if r.success and r.company_information]
        
        if not successful_results:
            return {
                "total_companies": len(results),
                "successful_extractions": 0,
                "success_rate": 0.0
            }
        
        # Calculate averages
        avg_confidence = sum(r.company_information.confidence_score for r in successful_results) / len(successful_results)
        avg_processing_time = sum(r.processing_time for r in results.values()) / len(results)
        
        # Industry distribution
        industries = {}
        for result in successful_results:
            industry = result.company_information.basic_info.industry
            if industry:
                industries[industry] = industries.get(industry, 0) + 1
        
        # Company size distribution
        company_sizes = {}
        for result in successful_results:
            size = result.company_information.basic_info.company_size
            if size:
                company_sizes[size] = company_sizes.get(size, 0) + 1
        
        return {
            "total_companies": len(results),
            "successful_extractions": len(successful_results),
            "success_rate": (len(successful_results) / len(results)) * 100,
            "avg_confidence_score": round(avg_confidence, 3),
            "avg_processing_time": round(avg_processing_time, 3),
            "industry_distribution": industries,
            "company_size_distribution": company_sizes,
            "companies_with_contact_info": sum(1 for r in successful_results if r.company_information.contact),
            "companies_with_social_media": sum(1 for r in successful_results if r.company_information.social_media),
            "companies_with_personnel": sum(1 for r in successful_results if r.company_information.key_personnel)
        }
    
    def register_progress_callback(
        self, 
        batch_id: str, 
        callback: Callable[[BatchProgressUpdate], Awaitable[None]]
    ):
        """Register progress callback for a batch."""
        self._progress_callbacks[batch_id] = callback
        logger.debug(f"Progress callback registered for batch: {batch_id}")
    
    def unregister_progress_callback(self, batch_id: str):
        """Unregister progress callback for a batch."""
        if batch_id in self._progress_callbacks:
            del self._progress_callbacks[batch_id]
            logger.debug(f"Progress callback unregistered for batch: {batch_id}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        scheduler_stats = self.scheduler.get_stats()
        
        # Calculate batch statistics
        total_batches = len(self._completed_batches) + len(self._active_batches)
        completed_batches = len([b for b in self._completed_batches.values() if b.status == BatchStatus.COMPLETED])
        partially_completed = len([b for b in self._completed_batches.values() if b.status == BatchStatus.PARTIALLY_COMPLETED])
        failed_batches = len([b for b in self._completed_batches.values() if b.status == BatchStatus.FAILED])
        
        # Get concurrent service stats if available
        concurrent_stats = {}
        if self._concurrent_service:
            try:
                concurrent_stats = await self._concurrent_service.get_performance_metrics()
            except Exception as e:
                logger.debug(f"Could not get concurrent service stats: {e}")
        
        return {
            "batch_scheduler": scheduler_stats,
            "batch_statistics": {
                "total_batches": total_batches,
                "active_batches": len(self._active_batches),
                "completed_batches": completed_batches,
                "partially_completed_batches": partially_completed,
                "failed_batches": failed_batches,
                "success_rate": (completed_batches / max(1, len(self._completed_batches))) * 100
            },
            "concurrent_extraction": concurrent_stats,
            "workers": {
                "active_workers": len(self._workers),
                "max_workers": self.scheduler.max_concurrent_batches
            }
        }