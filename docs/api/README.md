# Company Information Extraction API Documentation

## Overview

The Company Information Extraction API provides comprehensive endpoints for extracting detailed company information from web sources using intelligent search and crawling. This API combines Google SERP search with advanced web crawling to gather company data including contact information, financial details, social media presence, and key personnel.

## Base URL

```
Production: https://api.your-domain.com
Development: http://localhost:8000
```

## Authentication

Currently, the API does not require authentication for basic usage. Rate limiting is applied per IP address.

**Note**: For production deployment, implement API key authentication as described in the [Security Documentation](../operations/security.md).

## Content Type

All API requests and responses use JSON format:
```
Content-Type: application/json
```

## API Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/company/extract` | POST | Extract company information |
| `/api/v1/company/search-and-extract` | POST | Simplified extraction interface |
| `/api/v1/company/extraction-scopes` | GET | Available extraction modes |
| `/api/v1/company/health` | GET | Service health check |
| `/api/v1/company/batch/submit` | POST | Submit batch extraction |
| `/api/v1/company/batch/{batch_id}/status` | GET | Get batch status |
| `/api/v1/company/batch/{batch_id}/results` | GET | Get batch results |
| `/api/v1/company/batch/stats` | GET | Batch processing statistics |

## Rate Limiting

- **Per IP**: 100 requests per minute
- **Batch Processing**: 10 concurrent batches per IP
- **Company Extraction**: 5 concurrent extractions per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Response Format

### Success Response Structure

```json
{
  "success": true,
  "data": {
    // Endpoint-specific data
  },
  "metadata": {
    "trace_id": "uuid-trace-id",
    "processing_time": 2.45,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Response Structure

```json
{
  "success": false,
  "error": {
    "type": "CompanyAnalysisError",
    "message": "Unable to extract company information",
    "details": "Specific error details",
    "trace_id": "uuid-trace-id"
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input parameters |
| 422 | Validation Error - Invalid request data |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
| 502 | Bad Gateway - External service error |
| 504 | Gateway Timeout |

## Getting Started

### Quick Start Example

```bash
curl -X POST "http://localhost:8000/api/v1/company/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "OpenAI",
    "extraction_mode": "comprehensive"
  }'
```

### Python Example

```python
import httpx
import asyncio

async def extract_company_info():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/extract",
            json={
                "company_name": "OpenAI",
                "domain": "openai.com",
                "extraction_mode": "comprehensive",
                "include_social_media": True,
                "include_financial_data": True
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Company: {result['data']['company_name']}")
            print(f"Industry: {result['data']['industry']}")
            print(f"Employees: {result['data']['employee_count']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.json())

asyncio.run(extract_company_info())
```

## Extraction Modes

The API supports different extraction modes optimized for various use cases:

### Basic Mode
- **Speed**: 15-30 seconds
- **Coverage**: Essential information only
- **Use Case**: Quick lookups, basic research

### Standard Mode (Default)
- **Speed**: 30-60 seconds  
- **Coverage**: Comprehensive information
- **Use Case**: General business intelligence

### Comprehensive Mode
- **Speed**: 45-90 seconds
- **Coverage**: Complete extraction with detailed analysis
- **Use Case**: Deep research, due diligence

### Contact Focused Mode
- **Speed**: 20-40 seconds
- **Coverage**: Prioritizes contact information
- **Use Case**: Sales prospecting, outreach

### Financial Focused Mode
- **Speed**: 30-60 seconds
- **Coverage**: Prioritizes financial data
- **Use Case**: Investment research, financial analysis

## SDKs and Client Libraries

### Python SDK

Install the official Python client:

```bash
pip install crawl4ai-company-client
```

Usage example:

```python
from crawl4ai_company import CompanyExtractor

# Initialize client
extractor = CompanyExtractor(base_url="http://localhost:8000")

# Extract company information
result = await extractor.extract(
    company_name="Microsoft",
    extraction_mode="comprehensive"
)

print(result.company_name)
print(result.industry)
print(result.financial_data)
```

### JavaScript/Node.js SDK

```bash
npm install crawl4ai-company-client
```

Usage example:

```javascript
const { CompanyExtractor } = require('crawl4ai-company-client');

const extractor = new CompanyExtractor({
  baseUrl: 'http://localhost:8000'
});

async function extractCompany() {
  try {
    const result = await extractor.extract({
      companyName: 'Google',
      extractionMode: 'comprehensive'
    });
    
    console.log(result.companyName);
    console.log(result.industry);
    console.log(result.contactInfo);
  } catch (error) {
    console.error('Extraction failed:', error);
  }
}
```

## Performance Optimization

### Caching

The API implements intelligent caching to improve performance:

- **Company Information**: Cached for 24 hours
- **SERP Results**: Cached for 6 hours  
- **Crawled Content**: Cached for 12 hours

### Batch Processing

For multiple companies, use the batch API for optimal performance:

```json
POST /api/v1/company/batch/submit
{
  "company_names": ["OpenAI", "Microsoft", "Google"],
  "extraction_mode": "standard",
  "priority": "high",
  "max_concurrent": 5
}
```

### Resource Management

The API automatically manages resources with:
- Connection pooling for HTTP requests
- Memory usage monitoring
- Automatic garbage collection
- Circuit breakers for external services

## Error Handling

### Common Error Types

1. **ValidationError**: Invalid request parameters
2. **CompanyAnalysisError**: Company extraction failed
3. **RateLimitError**: Rate limit exceeded
4. **TimeoutError**: Request timeout
5. **ServiceUnavailableError**: External service unavailable

### Retry Strategy

Implement exponential backoff for retries:

```python
import asyncio
import random

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)
```

## Next Steps

- Review individual [endpoint documentation](./endpoints/)
- Explore [integration examples](../user/integration-examples/)
- Check [deployment guides](../deployment/)
- Set up [monitoring and alerts](../operations/)

## Support

For technical support and questions:
- Documentation: See [User Guide](../user/)
- Issues: GitHub repository issues
- Performance: See [Performance Guide](../user/performance-guide.md)