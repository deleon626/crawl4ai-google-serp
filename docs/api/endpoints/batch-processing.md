# Batch Processing API Endpoints

Process multiple companies efficiently with batch processing capabilities, priority queuing, and comprehensive progress tracking.

## POST /api/v1/company/batch/submit

Submit a batch of companies for extraction processing.

### Request

#### Headers
```
Content-Type: application/json
```

#### Request Body

```json
{
  "company_names": ["string"],
  "extraction_mode": "basic|standard|comprehensive|contact_focused|financial_focused",
  "priority": "low|normal|high|urgent",
  "country": "string (optional, default: US)",
  "language": "string (optional, default: en)",
  "domain_hints": {
    "company_name": "domain.com"
  },
  "max_concurrent": "integer (optional, default: 5, max: 20)",
  "timeout_seconds": "integer (optional, default: 300, max: 600)",
  "include_failed_results": "boolean (optional, default: true)",
  "export_format": "json|csv|excel (optional, default: json)"
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `company_names` | array | Yes | - | List of company names (1-100 companies) |
| `extraction_mode` | enum | No | "standard" | Extraction mode for all companies |
| `priority` | enum | No | "normal" | Processing priority (low/normal/high/urgent) |
| `country` | string | No | "US" | Country code for search localization |
| `language` | string | No | "en" | Language code for search localization |
| `domain_hints` | object | No | {} | Optional domain mappings for companies |
| `max_concurrent` | integer | No | 5 | Max concurrent extractions (1-20) |
| `timeout_seconds` | integer | No | 300 | Timeout per company (30-600 seconds) |
| `include_failed_results` | boolean | No | true | Include failed extractions in results |
| `export_format` | enum | No | "json" | Export format (json/csv/excel) |

### Response

#### Success Response (202 Accepted)

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_20240115_abc123",
    "status": "queued",
    "message": "Batch submitted successfully",
    "total_companies": 25,
    "estimated_processing_time": 450.5,
    "priority": "high",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "metadata": {
    "trace_id": "batch_submit_def456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Code Examples

#### cURL Example

```bash
curl -X POST "http://localhost:8000/api/v1/company/batch/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "company_names": ["OpenAI", "Microsoft", "Google", "Tesla"],
    "extraction_mode": "comprehensive",
    "priority": "high",
    "max_concurrent": 3,
    "export_format": "json"
  }'
```

#### Python Example

```python
import httpx
import asyncio

async def submit_batch():
    companies = [
        "Apple", "Microsoft", "Google", "Amazon", "Tesla",
        "Meta", "Netflix", "Nvidia", "Adobe", "Salesforce"
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/batch/submit",
            json={
                "company_names": companies,
                "extraction_mode": "standard",
                "priority": "normal",
                "max_concurrent": 5,
                "timeout_seconds": 180,
                "export_format": "csv"
            }
        )
        
        if response.status_code == 202:
            data = response.json()["data"]
            batch_id = data["batch_id"]
            print(f"Batch submitted: {batch_id}")
            print(f"Estimated time: {data['estimated_processing_time']} seconds")
            return batch_id
        else:
            print(f"Error: {response.json()}")

batch_id = asyncio.run(submit_batch())
```

---

## GET /api/v1/company/batch/{batch_id}/status

Get the current status and progress of a batch processing job.

### Request

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | The batch ID returned from submit endpoint |

### Response

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_20240115_abc123",
    "status": "processing",
    "progress": {
      "total_companies": 25,
      "completed": 15,
      "failed": 2,
      "remaining": 8,
      "completion_percentage": 68.0,
      "current_phase": "extraction"
    },
    "processing_time": 285.7,
    "created_at": "2024-01-15T10:30:00Z",
    "started_at": "2024-01-15T10:31:15Z",
    "estimated_completion": "2024-01-15T10:45:30Z",
    "last_update": "2024-01-15T10:39:42Z",
    "priority": "high",
    "extraction_mode": "comprehensive",
    "export_format": "json"
  },
  "metadata": {
    "trace_id": "batch_status_ghi789",
    "timestamp": "2024-01-15T10:40:00Z"
  }
}
```

#### Batch Status Values

| Status | Description |
|--------|-------------|
| `queued` | Batch is waiting to be processed |
| `processing` | Batch is currently being processed |
| `completed` | Batch processing completed successfully |
| `failed` | Batch processing failed |
| `cancelled` | Batch processing was cancelled |
| `paused` | Batch processing is paused |

### Code Example

```python
import httpx
import asyncio
import time

async def monitor_batch(batch_id: str):
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"http://localhost:8000/api/v1/company/batch/{batch_id}/status"
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                progress = data["progress"]
                
                print(f"Status: {data['status']}")
                print(f"Progress: {progress['completed']}/{progress['total_companies']} "
                      f"({progress['completion_percentage']:.1f}%)")
                
                if data["status"] in ["completed", "failed", "cancelled"]:
                    print(f"Final status: {data['status']}")
                    break
                    
                await asyncio.sleep(10)  # Check every 10 seconds
            else:
                print(f"Error checking status: {response.json()}")
                break

asyncio.run(monitor_batch("batch_20240115_abc123"))
```

---

## GET /api/v1/company/batch/{batch_id}/results

Retrieve the results from a completed batch processing job.

### Request

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | The batch ID of completed batch |

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | No | "json" | Response format (json/csv/excel) |
| `include_failed` | boolean | No | true | Include failed extraction results |
| `download` | boolean | No | false | Return as downloadable file |

### Response

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_20240115_abc123",
    "status": "completed",
    "total_companies": 25,
    "successful_extractions": 23,
    "failed_extractions": 2,
    "processing_time": 675.3,
    "completed_at": "2024-01-15T10:45:30Z",
    "results": [
      {
        "company_name": "OpenAI",
        "extraction_status": "success",
        "data": {
          "company_name": "OpenAI",
          "domain": "openai.com",
          "industry": "Artificial Intelligence",
          "employee_count": "501-1000",
          "headquarters": {
            "city": "San Francisco",
            "state": "California",
            "country": "United States"
          },
          "financial_data": {
            "valuation": "$86B",
            "funding_raised": "$11.3B"
          }
        }
      },
      {
        "company_name": "NonExistentCompany",
        "extraction_status": "failed",
        "error": {
          "type": "CompanyAnalysisError",
          "message": "Company not found in search results",
          "details": "No web presence found for specified company"
        }
      }
    ],
    "summary": {
      "industries": {
        "Technology": 12,
        "Healthcare": 5,
        "Finance": 4,
        "Manufacturing": 2
      },
      "company_sizes": {
        "1-50": 3,
        "51-200": 8,
        "201-1000": 7,
        "1000+": 5
      },
      "countries": {
        "United States": 18,
        "United Kingdom": 3,
        "Canada": 2
      }
    },
    "export_url": "/api/v1/company/batch/batch_20240115_abc123/download"
  },
  "metadata": {
    "trace_id": "batch_results_jkl012",
    "timestamp": "2024-01-15T10:50:00Z"
  }
}
```

### Code Examples

#### Python Example with Pandas Export

```python
import httpx
import pandas as pd
import asyncio

async def get_batch_results(batch_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/company/batch/{batch_id}/results"
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            
            # Convert to DataFrame
            results = []
            for result in data["results"]:
                if result["extraction_status"] == "success":
                    company_data = result["data"]
                    flattened = {
                        "company_name": company_data["company_name"],
                        "domain": company_data.get("domain"),
                        "industry": company_data.get("industry"),
                        "employee_count": company_data.get("employee_count"),
                        "headquarters_city": company_data.get("headquarters", {}).get("city"),
                        "headquarters_country": company_data.get("headquarters", {}).get("country"),
                        "valuation": company_data.get("financial_data", {}).get("valuation"),
                        "funding_raised": company_data.get("financial_data", {}).get("funding_raised")
                    }
                    results.append(flattened)
            
            df = pd.DataFrame(results)
            df.to_csv(f"batch_{batch_id}_results.csv", index=False)
            print(f"Exported {len(results)} companies to CSV")
            
            # Print summary
            print(f"\nBatch Summary:")
            print(f"Total: {data['total_companies']}")
            print(f"Successful: {data['successful_extractions']}")
            print(f"Failed: {data['failed_extractions']}")
            print(f"Processing time: {data['processing_time']:.1f}s")
            
        else:
            print(f"Error retrieving results: {response.json()}")

asyncio.run(get_batch_results("batch_20240115_abc123"))
```

---

## GET /api/v1/company/batch/stats

Get statistics about batch processing system performance and usage.

### Request

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `timeframe` | string | No | "24h" | Statistics timeframe (1h/6h/24h/7d/30d) |
| `include_details` | boolean | No | false | Include detailed statistics |

### Response

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "timeframe": "24h",
    "system_stats": {
      "total_batches": 45,
      "completed_batches": 38,
      "failed_batches": 3,
      "active_batches": 4,
      "total_companies_processed": 1247,
      "average_processing_time": 156.7,
      "success_rate": 94.2
    },
    "performance_metrics": {
      "average_batch_size": 27.7,
      "fastest_batch_time": 89.3,
      "slowest_batch_time": 847.2,
      "most_common_extraction_mode": "standard",
      "peak_concurrent_batches": 8,
      "cache_hit_rate": 72.4
    },
    "resource_utilization": {
      "cpu_usage": 67.3,
      "memory_usage": 45.8,
      "active_connections": 23,
      "queue_size": 12
    },
    "error_analysis": {
      "most_common_errors": [
        {
          "error_type": "CompanyAnalysisError",
          "count": 89,
          "percentage": 67.4
        },
        {
          "error_type": "TimeoutError", 
          "count": 28,
          "percentage": 21.2
        }
      ]
    }
  },
  "metadata": {
    "generated_at": "2024-01-15T10:50:00Z",
    "trace_id": "batch_stats_mno345"
  }
}
```

### Batch Processing Best Practices

#### 1. Optimal Batch Size

```python
# Recommended batch sizes by extraction mode
batch_sizes = {
    "basic": 50,        # Fast, can handle more
    "standard": 25,     # Balanced
    "comprehensive": 10, # Slow, smaller batches
    "contact_focused": 30,
    "financial_focused": 20
}
```

#### 2. Priority Management

```python
# Use priority levels effectively
priorities = {
    "urgent": "Real-time business needs (< 5 companies)",
    "high": "Important research (5-20 companies)", 
    "normal": "Regular processing (20-50 companies)",
    "low": "Background tasks (50+ companies)"
}
```

#### 3. Error Handling and Retries

```python
import httpx
import asyncio

async def robust_batch_processing(companies: list):
    max_retries = 3
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/company/batch/submit",
                    json={
                        "company_names": companies,
                        "extraction_mode": "standard",
                        "priority": "normal",
                        "timeout_seconds": 300
                    }
                )
                
                if response.status_code == 202:
                    return response.json()["data"]["batch_id"]
                    
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise e
```

#### 4. Progress Monitoring

```python
async def monitor_with_notifications(batch_id: str):
    """Monitor batch with progress notifications"""
    last_percentage = 0
    
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"http://localhost:8000/api/v1/company/batch/{batch_id}/status"
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                progress = data["progress"]
                current_percentage = progress["completion_percentage"]
                
                # Notify on significant progress
                if current_percentage - last_percentage >= 10:
                    print(f"Progress update: {current_percentage:.1f}% complete")
                    last_percentage = current_percentage
                
                if data["status"] in ["completed", "failed"]:
                    break
                    
                await asyncio.sleep(15)
            else:
                break
```

### Performance Optimization

#### 1. Batch Size Optimization

- **Small batches (1-10)**: Use for urgent requests or when results needed quickly
- **Medium batches (11-50)**: Optimal for most use cases, balance speed and resource usage
- **Large batches (51-100)**: Use for background processing when time is not critical

#### 2. Concurrent Processing

```python
# Optimal concurrency settings
concurrency_by_mode = {
    "basic": 10,        # Lightweight, can handle more
    "standard": 5,      # Balanced
    "comprehensive": 3,  # Resource intensive
    "contact_focused": 7,
    "financial_focused": 4
}
```

#### 3. Resource Management

Monitor system resources and adjust batch parameters:

```python
async def adaptive_batch_processing(companies: list):
    # Get current system stats
    stats_response = await client.get("/api/v1/company/batch/stats")
    stats = stats_response.json()["data"]["resource_utilization"]
    
    # Adjust batch size based on system load
    if stats["cpu_usage"] > 80:
        max_concurrent = 2
        batch_size = min(10, len(companies))
    elif stats["cpu_usage"] > 60:
        max_concurrent = 3
        batch_size = min(20, len(companies))
    else:
        max_concurrent = 5
        batch_size = min(50, len(companies))
    
    # Submit with optimized parameters
    return await submit_batch_with_params(
        companies, max_concurrent, batch_size
    )
```

### Troubleshooting

#### Common Issues

1. **Batch Stuck in Processing**
   - Check system resources with `/batch/stats`
   - Verify no external service outages
   - Consider cancelling and resubmitting with smaller batch

2. **High Failure Rate**
   - Review error analysis in batch stats
   - Verify company names are accurate
   - Check if domain hints would help

3. **Slow Processing**
   - Use simpler extraction mode
   - Reduce `max_concurrent` parameter
   - Split into smaller batches

4. **Export Issues**
   - Ensure batch is completed before requesting results
   - Check available disk space for large exports
   - Use streaming downloads for very large results

### Related Endpoints

- [Company Extraction](./company-extraction.md) - Single company extraction
- [Health Check](./health-check.md) - Service status
- [Export Downloads](./export-downloads.md) - Download processed results