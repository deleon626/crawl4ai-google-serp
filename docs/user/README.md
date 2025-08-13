# User Guide

Welcome to the Company Information Extraction API! This guide provides everything you need to start extracting comprehensive company information using our intelligent web crawling and search capabilities.

## What is the Company Information Extraction API?

The Company Information Extraction API is a powerful service that automatically gathers comprehensive company information from the web using:

- **Intelligent Search**: Google SERP API integration for finding company information
- **Advanced Web Crawling**: Crawl4ai-powered content extraction from company websites
- **Data Intelligence**: Structured parsing and analysis of company data
- **Batch Processing**: Efficient processing of multiple companies simultaneously
- **Performance Optimization**: Advanced caching and concurrent processing

## Key Features

### 🔍 **Comprehensive Data Extraction**
- Company overview, industry, and description
- Contact information (email, phone, address)
- Financial data (revenue, funding, valuation)
- Social media profiles and online presence
- Key personnel and leadership information
- Products, services, and competitive analysis

### ⚡ **High Performance**
- Multiple extraction modes (15s to 90s processing time)
- Intelligent caching for faster repeat requests
- Batch processing for multiple companies
- Concurrent processing capabilities
- Resource optimization and monitoring

### 🛡️ **Enterprise Ready**
- Rate limiting and security features
- Comprehensive error handling
- Detailed logging and monitoring
- Health checks and service monitoring
- Production-ready deployment options

## Quick Start

### 1. API Access

The API is available at:
```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

### 2. Your First Request

Extract basic company information:

```bash
curl -X POST "http://localhost:8000/api/v1/company/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "OpenAI",
    "extraction_mode": "basic"
  }'
```

### 3. Understanding the Response

```json
{
  "success": true,
  "data": {
    "company_name": "OpenAI",
    "domain": "openai.com",
    "industry": "Artificial Intelligence",
    "description": "OpenAI is an AI research and deployment company...",
    "employee_count": "501-1000",
    "headquarters": {
      "city": "San Francisco",
      "state": "California",
      "country": "United States"
    },
    "contact_info": {
      "website": "https://openai.com",
      "email": "support@openai.com"
    },
    "financial_data": {
      "valuation": "$86B",
      "funding_raised": "$11.3B"
    }
  },
  "metadata": {
    "processing_time": 18.5,
    "confidence_score": 0.92
  }
}
```

## Extraction Modes

Choose the right extraction mode for your needs:

### 🚀 Basic Mode (15-30 seconds)
**Best for**: Quick validation, basic research
```json
{
  "company_name": "Tesla",
  "extraction_mode": "basic"
}
```
**Returns**: Essential company information (~15-20 data points)

### 📊 Standard Mode (30-60 seconds)
**Best for**: General business intelligence, competitive analysis
```json
{
  "company_name": "Microsoft",
  "extraction_mode": "standard"
}
```
**Returns**: Comprehensive company profile (~30-40 data points)

### 🔍 Comprehensive Mode (45-90 seconds)
**Best for**: Due diligence, detailed research, investment analysis
```json
{
  "company_name": "Google",
  "extraction_mode": "comprehensive"
}
```
**Returns**: Complete extraction with detailed analysis (~50+ data points)

### 📞 Contact Focused Mode (20-40 seconds)
**Best for**: Sales prospecting, outreach campaigns
```json
{
  "company_name": "Salesforce",
  "extraction_mode": "contact_focused"
}
```
**Returns**: Prioritizes contact information and personnel data

### 💰 Financial Focused Mode (30-60 seconds)
**Best for**: Investment research, financial analysis
```json
{
  "company_name": "Stripe",
  "extraction_mode": "financial_focused"
}
```
**Returns**: Emphasizes financial data, funding, and business metrics

## Use Cases and Examples

### Use Case 1: Sales Prospecting

Extract contact information for outreach:

```python
import httpx
import asyncio

async def prospect_company(company_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/extract",
            json={
                "company_name": company_name,
                "extraction_mode": "contact_focused",
                "include_key_personnel": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            
            print(f"Company: {data['company_name']}")
            print(f"Website: {data['contact_info'].get('website')}")
            print(f"Email: {data['contact_info'].get('email')}")
            
            print("\nKey Personnel:")
            for person in data.get('key_personnel', [])[:3]:
                print(f"- {person['name']}: {person['position']}")
        
        return data

# Example usage
company_data = asyncio.run(prospect_company("HubSpot"))
```

### Use Case 2: Competitive Analysis

Research multiple competitors:

```python
async def competitive_analysis(competitors: list):
    results = []
    
    async with httpx.AsyncClient() as client:
        for company in competitors:
            response = await client.post(
                "http://localhost:8000/api/v1/company/extract",
                json={
                    "company_name": company,
                    "extraction_mode": "standard",
                    "include_financial_data": True
                }
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                results.append({
                    "name": data['company_name'],
                    "employees": data.get('employee_count'),
                    "industry": data.get('industry'),
                    "valuation": data.get('financial_data', {}).get('valuation'),
                    "headquarters": data.get('headquarters', {}).get('city')
                })
    
    # Create comparison report
    for result in results:
        print(f"{result['name']}: {result['employees']} employees, "
              f"valued at {result['valuation']}")

# Analyze CRM competitors
competitors = ["Salesforce", "HubSpot", "Pipedrive", "Zoho"]
asyncio.run(competitive_analysis(competitors))
```

### Use Case 3: Investment Research

Deep financial analysis for investment decisions:

```python
async def investment_research(company_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/extract",
            json={
                "company_name": company_name,
                "extraction_mode": "financial_focused",
                "include_financial_data": True,
                "include_key_personnel": True,
                "max_pages_to_crawl": 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            financial = data.get('financial_data', {})
            
            print(f"=== {data['company_name']} Investment Analysis ===")
            print(f"Industry: {data.get('industry')}")
            print(f"Founded: {data.get('founded_year')}")
            print(f"Employees: {data.get('employee_count')}")
            print(f"Valuation: {financial.get('valuation')}")
            print(f"Revenue: {financial.get('revenue')}")
            print(f"Funding Raised: {financial.get('funding_raised')}")
            print(f"Last Funding: {financial.get('last_funding_round')}")
            
            if financial.get('investors'):
                print(f"Key Investors: {', '.join(financial['investors'][:3])}")

# Research a potential investment
asyncio.run(investment_research("Stripe"))
```

### Use Case 4: Batch Processing for Market Research

Process multiple companies efficiently:

```python
async def market_research(industry_companies: list):
    # Submit batch request
    async with httpx.AsyncClient() as client:
        batch_response = await client.post(
            "http://localhost:8000/api/v1/company/batch/submit",
            json={
                "company_names": industry_companies,
                "extraction_mode": "standard",
                "priority": "normal",
                "export_format": "json"
            }
        )
        
        batch_id = batch_response.json()["data"]["batch_id"]
        print(f"Batch submitted: {batch_id}")
        
        # Monitor progress
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/company/batch/{batch_id}/status"
            )
            
            status_data = status_response.json()["data"]
            progress = status_data["progress"]
            
            print(f"Progress: {progress['completed']}/{progress['total_companies']} "
                  f"({progress['completion_percentage']:.1f}%)")
            
            if status_data["status"] == "completed":
                break
                
            await asyncio.sleep(10)
        
        # Get results
        results_response = await client.get(
            f"http://localhost:8000/api/v1/company/batch/{batch_id}/results"
        )
        
        return results_response.json()["data"]

# Research fintech companies
fintech_companies = [
    "Stripe", "Square", "Plaid", "Robinhood", "Coinbase",
    "PayPal", "Klarna", "Affirm", "Brex", "Chime"
]

results = asyncio.run(market_research(fintech_companies))
```

## Best Practices

### 1. Choosing the Right Extraction Mode

```python
# Decision matrix for extraction modes
def choose_extraction_mode(use_case: str, time_constraint: str, data_depth: str):
    if time_constraint == "urgent" and data_depth == "basic":
        return "basic"
    elif use_case == "sales" and data_depth == "contact":
        return "contact_focused"
    elif use_case == "investment" and data_depth == "financial":
        return "financial_focused"
    elif data_depth == "comprehensive":
        return "comprehensive"
    else:
        return "standard"
```

### 2. Error Handling

Implement robust error handling for production use:

```python
import asyncio
import httpx
from typing import Optional, Dict, Any

async def extract_with_retry(
    company_name: str, 
    max_retries: int = 3,
    backoff_factor: float = 1.0
) -> Optional[Dict[Any, Any]]:
    """Extract company data with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/company/extract",
                    json={
                        "company_name": company_name,
                        "extraction_mode": "standard",
                        "timeout_seconds": 120
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["data"]
                elif response.status_code == 429:  # Rate limited
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    error = response.json().get("error", {})
                    print(f"API Error: {error.get('message')}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff_factor * (2 ** attempt))
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    print(f"Failed to extract data for {company_name} after {max_retries} attempts")
    return None
```

### 3. Rate Limiting Management

Respect API rate limits in your applications:

```python
import asyncio
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def wait_if_needed(self):
        now = time.time()
        
        # Remove old requests outside time window
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            wait_time = self.requests[0] + self.time_window - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.requests.append(now)

# Use rate limiter
rate_limiter = RateLimiter(max_requests=50, time_window=60)  # 50 requests per minute

async def rate_limited_extraction(company_name: str):
    await rate_limiter.wait_if_needed()
    return await extract_with_retry(company_name)
```

### 4. Data Validation and Cleaning

Validate and clean extracted data:

```python
from typing import Dict, Any, Optional

def validate_company_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean company data."""
    cleaned_data = {}
    
    # Required fields
    cleaned_data["company_name"] = data.get("company_name", "").strip()
    if not cleaned_data["company_name"]:
        raise ValueError("Company name is required")
    
    # Optional fields with validation
    if "domain" in data and data["domain"]:
        domain = data["domain"].lower().strip()
        if domain.startswith("http"):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc
        cleaned_data["domain"] = domain
    
    # Financial data validation
    if "financial_data" in data:
        financial = data["financial_data"]
        cleaned_financial = {}
        
        # Clean monetary values
        for field in ["revenue", "valuation", "funding_raised"]:
            if field in financial and financial[field]:
                value = financial[field].replace("$", "").replace(",", "")
                if value and not value.lower() in ["unknown", "n/a"]:
                    cleaned_financial[field] = f"${value}"
        
        if cleaned_financial:
            cleaned_data["financial_data"] = cleaned_financial
    
    # Employee count normalization
    if "employee_count" in data and data["employee_count"]:
        employee_count = data["employee_count"]
        if isinstance(employee_count, str) and "-" in employee_count:
            cleaned_data["employee_count"] = employee_count
        elif isinstance(employee_count, (int, float)):
            cleaned_data["employee_count"] = str(int(employee_count))
    
    return cleaned_data

# Usage
try:
    raw_data = await extract_with_retry("Tesla")
    if raw_data:
        clean_data = validate_company_data(raw_data)
        print(f"Validated data for {clean_data['company_name']}")
except ValueError as e:
    print(f"Data validation error: {e}")
```

## Performance Optimization

### 1. Caching Strategy

Implement client-side caching for better performance:

```python
import json
import time
from typing import Dict, Any, Optional
import os

class CompanyDataCache:
    def __init__(self, cache_dir: str = "./cache", ttl: int = 3600):
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, company_name: str) -> str:
        safe_name = "".join(c for c in company_name if c.isalnum() or c in "- ").strip()
        return os.path.join(self.cache_dir, f"{safe_name.lower()}.json")
    
    def get(self, company_name: str) -> Optional[Dict[str, Any]]:
        cache_path = self._get_cache_path(company_name)
        
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid
                if time.time() - cached_data["timestamp"] < self.ttl:
                    return cached_data["data"]
        except Exception:
            pass
        
        return None
    
    def set(self, company_name: str, data: Dict[str, Any]):
        cache_path = self._get_cache_path(company_name)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "data": data
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to cache data: {e}")

# Usage with caching
cache = CompanyDataCache(ttl=3600)  # 1 hour cache

async def extract_with_cache(company_name: str) -> Optional[Dict[str, Any]]:
    # Check cache first
    cached_data = cache.get(company_name)
    if cached_data:
        print(f"Using cached data for {company_name}")
        return cached_data
    
    # Extract from API
    data = await extract_with_retry(company_name)
    if data:
        cache.set(company_name, data)
    
    return data
```

### 2. Concurrent Processing

Process multiple companies efficiently:

```python
import asyncio
from typing import List, Dict, Any

async def extract_companies_concurrently(
    company_names: List[str], 
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """Extract multiple companies with controlled concurrency."""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}
    
    async def extract_single(company_name: str):
        async with semaphore:
            try:
                data = await extract_with_cache(company_name)
                results[company_name] = {
                    "success": True,
                    "data": data
                }
            except Exception as e:
                results[company_name] = {
                    "success": False,
                    "error": str(e)
                }
    
    # Start all extractions concurrently
    tasks = [extract_single(company) for company in company_names]
    await asyncio.gather(*tasks)
    
    return results

# Usage
companies = ["Apple", "Microsoft", "Google", "Amazon", "Tesla"]
results = asyncio.run(extract_companies_concurrently(companies, max_concurrent=3))

# Print results
for company, result in results.items():
    if result["success"]:
        print(f"✅ {company}: {result['data']['industry']}")
    else:
        print(f"❌ {company}: {result['error']}")
```

## Integration Examples

### Integration with Popular Tools

#### Pandas DataFrame Export

```python
import pandas as pd
from typing import List, Dict, Any

async def create_company_dataframe(company_names: List[str]) -> pd.DataFrame:
    """Extract companies and create a pandas DataFrame."""
    
    results = await extract_companies_concurrently(company_names)
    
    # Flatten data for DataFrame
    flattened_data = []
    for company_name, result in results.items():
        if result["success"] and result["data"]:
            data = result["data"]
            flattened_data.append({
                "company_name": data.get("company_name"),
                "domain": data.get("domain"),
                "industry": data.get("industry"),
                "employee_count": data.get("employee_count"),
                "headquarters_city": data.get("headquarters", {}).get("city"),
                "headquarters_country": data.get("headquarters", {}).get("country"),
                "website": data.get("contact_info", {}).get("website"),
                "email": data.get("contact_info", {}).get("email"),
                "valuation": data.get("financial_data", {}).get("valuation"),
                "funding_raised": data.get("financial_data", {}).get("funding_raised"),
                "founded_year": data.get("founded_year")
            })
    
    return pd.DataFrame(flattened_data)

# Usage
companies = ["Stripe", "Plaid", "Square", "PayPal", "Robinhood"]
df = asyncio.run(create_company_dataframe(companies))

# Export to various formats
df.to_csv("company_data.csv", index=False)
df.to_excel("company_data.xlsx", index=False)
print(df.head())
```

#### CRM Integration (Salesforce)

```python
from simple_salesforce import Salesforce

async def sync_to_salesforce(company_names: List[str], sf_credentials: Dict[str, str]):
    """Extract companies and sync to Salesforce."""
    
    # Initialize Salesforce connection
    sf = Salesforce(**sf_credentials)
    
    # Extract company data
    results = await extract_companies_concurrently(company_names)
    
    for company_name, result in results.items():
        if result["success"] and result["data"]:
            data = result["data"]
            
            # Create Salesforce account record
            account_data = {
                "Name": data.get("company_name"),
                "Website": data.get("contact_info", {}).get("website"),
                "Industry": data.get("industry"),
                "NumberOfEmployees": data.get("employee_count"),
                "BillingCity": data.get("headquarters", {}).get("city"),
                "BillingCountry": data.get("headquarters", {}).get("country"),
                "Description": data.get("description", "")[:32000]  # Salesforce limit
            }
            
            try:
                sf.Account.create(account_data)
                print(f"✅ Created Salesforce account for {company_name}")
            except Exception as e:
                print(f"❌ Failed to create account for {company_name}: {e}")
```

## Error Handling and Troubleshooting

### Common Error Types

1. **CompanyAnalysisError**: Company not found or data extraction failed
2. **ValidationError**: Invalid request parameters
3. **RateLimitError**: Rate limit exceeded
4. **TimeoutError**: Request timeout
5. **ServiceUnavailableError**: External service unavailable

### Troubleshooting Guide

#### Issue: Company Not Found

```python
# Solutions for company not found errors
async def extract_with_fallbacks(company_name: str):
    # Try standard extraction first
    try:
        return await extract_with_retry(company_name)
    except Exception:
        pass
    
    # Try with domain if available
    if "." in company_name:
        try:
            return await extract_with_retry(company_name, domain=company_name)
        except Exception:
            pass
    
    # Try variations of the company name
    variations = [
        f"{company_name} Inc",
        f"{company_name} Corporation",
        f"{company_name} Ltd",
        company_name.replace(" ", "")
    ]
    
    for variation in variations:
        try:
            return await extract_with_retry(variation)
        except Exception:
            continue
    
    return None
```

#### Issue: Slow Performance

```python
# Performance optimization strategies
async def optimize_extraction(company_names: List[str]):
    # Use basic mode for faster results
    fast_results = await extract_companies_concurrently(
        company_names, 
        extraction_mode="basic",
        max_concurrent=10
    )
    
    # Only do comprehensive extraction for successful basic extractions
    comprehensive_candidates = [
        name for name, result in fast_results.items() 
        if result["success"]
    ]
    
    comprehensive_results = await extract_companies_concurrently(
        comprehensive_candidates,
        extraction_mode="comprehensive", 
        max_concurrent=3
    )
    
    return comprehensive_results
```

## Advanced Features

### Custom Extraction Parameters

Fine-tune extraction behavior:

```python
async def custom_extraction(company_name: str):
    return await client.post(
        "http://localhost:8000/api/v1/company/extract",
        json={
            "company_name": company_name,
            "extraction_mode": "comprehensive",
            "country": "US",  # Localize search
            "language": "en",  # Search language
            "include_social_media": True,
            "include_financial_data": True,
            "include_contact_info": True,
            "include_key_personnel": True,
            "max_pages_to_crawl": 10,  # Crawl more pages
            "timeout_seconds": 180  # Longer timeout
        }
    )
```

### Webhooks for Batch Processing

Set up webhooks to get notified when batch processing completes:

```python
from fastapi import FastAPI, Request
import asyncio

app = FastAPI()

@app.post("/webhook/batch-complete")
async def batch_complete_webhook(request: Request):
    data = await request.json()
    batch_id = data["batch_id"]
    status = data["status"]
    
    if status == "completed":
        # Process completed batch
        await process_batch_results(batch_id)
    
    return {"status": "received"}

async def submit_batch_with_webhook(company_names: List[str]):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/batch/submit",
            json={
                "company_names": company_names,
                "extraction_mode": "standard",
                "webhook_url": "https://yourapp.com/webhook/batch-complete"
            }
        )
        return response.json()["data"]["batch_id"]
```

## SDK Development

### Creating a Python SDK Wrapper

```python
# company_extractor_sdk.py
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    company_name: str
    domain: Optional[str]
    industry: Optional[str]
    description: Optional[str]
    employee_count: Optional[str]
    headquarters: Optional[Dict[str, str]]
    contact_info: Optional[Dict[str, str]]
    financial_data: Optional[Dict[str, str]]
    social_media: Optional[Dict[str, str]]
    key_personnel: Optional[List[Dict[str, str]]]
    processing_time: float
    confidence_score: float

class CompanyExtractor:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self._client = None
    
    async def __aenter__(self):
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=300
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def extract(
        self,
        company_name: str,
        extraction_mode: str = "standard",
        **kwargs
    ) -> Optional[ExtractionResult]:
        """Extract company information."""
        
        response = await self._client.post(
            "/api/v1/company/extract",
            json={
                "company_name": company_name,
                "extraction_mode": extraction_mode,
                **kwargs
            }
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            metadata = response.json()["metadata"]
            
            return ExtractionResult(
                company_name=data.get("company_name"),
                domain=data.get("domain"),
                industry=data.get("industry"),
                description=data.get("description"),
                employee_count=data.get("employee_count"),
                headquarters=data.get("headquarters"),
                contact_info=data.get("contact_info"),
                financial_data=data.get("financial_data"),
                social_media=data.get("social_media"),
                key_personnel=data.get("key_personnel"),
                processing_time=metadata.get("processing_time", 0),
                confidence_score=metadata.get("confidence_score", 0)
            )
        else:
            raise Exception(f"API Error: {response.text}")
    
    async def extract_batch(
        self,
        company_names: List[str],
        extraction_mode: str = "standard",
        **kwargs
    ) -> str:
        """Submit batch extraction and return batch ID."""
        
        response = await self._client.post(
            "/api/v1/company/batch/submit",
            json={
                "company_names": company_names,
                "extraction_mode": extraction_mode,
                **kwargs
            }
        )
        
        if response.status_code == 202:
            return response.json()["data"]["batch_id"]
        else:
            raise Exception(f"Batch submission failed: {response.text}")

# Usage example
async def main():
    async with CompanyExtractor() as extractor:
        result = await extractor.extract(
            "OpenAI",
            extraction_mode="comprehensive"
        )
        
        if result:
            print(f"Company: {result.company_name}")
            print(f"Industry: {result.industry}")
            print(f"Employees: {result.employee_count}")
            print(f"Processing time: {result.processing_time}s")
            print(f"Confidence: {result.confidence_score}")

asyncio.run(main())
```

## Next Steps

1. **Explore API Documentation**: Review detailed [API endpoints documentation](../api/)
2. **Set Up Development Environment**: Follow the [deployment guide](../deployment/)
3. **Try Advanced Features**: Experiment with batch processing and custom parameters
4. **Integrate with Your Tools**: Use the integration examples as starting points
5. **Monitor Performance**: Set up monitoring as described in [operations guide](../operations/)

## Need Help?

- **Documentation**: Browse the complete [documentation](../)
- **Examples**: Check the [examples repository](../../examples/)
- **Performance**: Review [performance optimization guide](./performance-guide.md)
- **Troubleshooting**: See [troubleshooting guide](./troubleshooting.md)
- **Support**: Contact technical support with questions