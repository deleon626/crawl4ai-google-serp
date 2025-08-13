# Company Extraction API Endpoint

## POST /api/v1/company/extract

Extract comprehensive company information from web sources using intelligent search and crawling.

### Request

#### Headers
```
Content-Type: application/json
```

#### Request Body

```json
{
  "company_name": "string",
  "domain": "string (optional)",
  "extraction_mode": "basic|standard|comprehensive|contact_focused|financial_focused",
  "country": "string (optional, default: US)",
  "language": "string (optional, default: en)",
  "include_social_media": "boolean (optional, default: true)",
  "include_financial_data": "boolean (optional, default: true)",
  "include_contact_info": "boolean (optional, default: true)",
  "include_key_personnel": "boolean (optional, default: true)",
  "max_pages_to_crawl": "integer (optional, default: 5, max: 20)",
  "timeout_seconds": "integer (optional, default: 60, max: 300)"
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `company_name` | string | Yes | - | The name of the company to extract information for |
| `domain` | string | No | - | Company domain (e.g., "openai.com"). If not provided, will be discovered |
| `extraction_mode` | enum | No | "standard" | Extraction mode (see Extraction Modes section) |
| `country` | string | No | "US" | 2-letter country code for search localization |
| `language` | string | No | "en" | 2-letter language code for search localization |
| `include_social_media` | boolean | No | true | Include social media profiles in extraction |
| `include_financial_data` | boolean | No | true | Include financial information in extraction |
| `include_contact_info` | boolean | No | true | Include contact information in extraction |
| `include_key_personnel` | boolean | No | true | Include key personnel information |
| `max_pages_to_crawl` | integer | No | 5 | Maximum number of pages to crawl (1-20) |
| `timeout_seconds` | integer | No | 60 | Timeout per extraction in seconds (30-300) |

#### Validation Rules

- `company_name`: 1-100 characters, required
- `domain`: Valid domain format (with or without protocol)
- `country`: 2-letter uppercase country code (ISO 3166-1)
- `language`: 2-letter lowercase language code (ISO 639-1)
- `max_pages_to_crawl`: Integer between 1 and 20
- `timeout_seconds`: Integer between 30 and 300

### Response

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "company_name": "OpenAI",
    "domain": "openai.com",
    "industry": "Artificial Intelligence",
    "description": "OpenAI is an AI research and deployment company...",
    "headquarters": {
      "address": "3180 18th St, San Francisco, CA 94110",
      "city": "San Francisco",
      "state": "California",
      "country": "United States",
      "postal_code": "94110"
    },
    "employee_count": "501-1000",
    "founded_year": 2015,
    "company_type": "Private",
    "financial_data": {
      "revenue": "$28M",
      "funding_raised": "$11.3B",
      "valuation": "$86B",
      "last_funding_round": "Series C",
      "investors": ["Microsoft", "Khosla Ventures", "Reid Hoffman"]
    },
    "contact_info": {
      "website": "https://openai.com",
      "email": "support@openai.com",
      "phone": "+1 (415) 555-0123",
      "support_email": "support@openai.com",
      "press_email": "press@openai.com"
    },
    "social_media": {
      "twitter": "https://twitter.com/openai",
      "linkedin": "https://linkedin.com/company/openai",
      "github": "https://github.com/openai",
      "youtube": "https://youtube.com/@openai",
      "facebook": null,
      "instagram": null
    },
    "key_personnel": [
      {
        "name": "Sam Altman",
        "position": "CEO",
        "profile_url": "https://linkedin.com/in/sam-altman",
        "bio": "CEO and co-founder of OpenAI..."
      },
      {
        "name": "Greg Brockman",
        "position": "President & Co-Founder",
        "profile_url": "https://linkedin.com/in/thegdb",
        "bio": "Co-founder and President of OpenAI..."
      }
    ],
    "products_services": [
      "GPT-4",
      "ChatGPT",
      "DALL·E",
      "API Platform"
    ],
    "competitors": [
      "Anthropic",
      "Google DeepMind",
      "Meta AI"
    ],
    "recent_news": [
      {
        "title": "OpenAI Launches GPT-4 Turbo",
        "url": "https://example.com/news/gpt4-turbo",
        "date": "2024-01-15",
        "source": "TechCrunch"
      }
    ]
  },
  "metadata": {
    "extraction_mode": "comprehensive",
    "pages_crawled": 8,
    "processing_time": 45.2,
    "cache_hit": false,
    "sources_found": 12,
    "confidence_score": 0.92,
    "extraction_timestamp": "2024-01-15T10:30:00Z",
    "trace_id": "comp_extract_abc123",
    "warnings": [],
    "errors": []
  }
}
```

#### Error Responses

##### Validation Error (422 Unprocessable Entity)

```json
{
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "Request validation failed",
    "details": {
      "company_name": ["Field required"],
      "max_pages_to_crawl": ["Value must be between 1 and 20"]
    },
    "trace_id": "comp_extract_error_456"
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

##### Company Analysis Error (502 Bad Gateway)

```json
{
  "success": false,
  "error": {
    "type": "CompanyAnalysisError",
    "message": "Unable to extract company information",
    "details": "Company not found in search results or website inaccessible",
    "trace_id": "comp_extract_error_789"
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

##### Rate Limit Error (429 Too Many Requests)

```json
{
  "success": false,
  "error": {
    "type": "RateLimitError",
    "message": "Rate limit exceeded",
    "details": "Maximum 5 concurrent extractions allowed per IP",
    "trace_id": "comp_extract_rate_101"
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "retry_after": 30
  }
}
```

### Extraction Modes

#### Basic Mode
- **Duration**: 15-30 seconds
- **Features**: Essential company information only
- **Data Points**: ~15-20 fields
- **Use Case**: Quick validation, basic research

#### Standard Mode (Default)
- **Duration**: 30-60 seconds
- **Features**: Comprehensive company profile
- **Data Points**: ~30-40 fields
- **Use Case**: Business intelligence, competitive analysis

#### Comprehensive Mode
- **Duration**: 45-90 seconds
- **Features**: Complete extraction with detailed analysis
- **Data Points**: ~50+ fields
- **Use Case**: Due diligence, detailed research

#### Contact Focused Mode
- **Duration**: 20-40 seconds
- **Features**: Prioritizes contact information
- **Data Points**: ~25-30 fields (contact-heavy)
- **Use Case**: Sales prospecting, outreach campaigns

#### Financial Focused Mode
- **Duration**: 30-60 seconds
- **Features**: Prioritizes financial and funding data
- **Data Points**: ~35-45 fields (financial-heavy)
- **Use Case**: Investment analysis, financial research

### Code Examples

#### cURL Example

```bash
# Basic extraction
curl -X POST "http://localhost:8000/api/v1/company/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Stripe",
    "extraction_mode": "basic"
  }'

# Comprehensive extraction with custom parameters
curl -X POST "http://localhost:8000/api/v1/company/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Microsoft",
    "domain": "microsoft.com",
    "extraction_mode": "comprehensive",
    "country": "US",
    "language": "en",
    "include_social_media": true,
    "include_financial_data": true,
    "max_pages_to_crawl": 10,
    "timeout_seconds": 120
  }'
```

#### Python Example

```python
import httpx
import asyncio

async def extract_company():
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            "http://localhost:8000/api/v1/company/extract",
            json={
                "company_name": "Tesla",
                "extraction_mode": "financial_focused",
                "include_key_personnel": True,
                "max_pages_to_crawl": 8
            }
        )
        
        if response.status_code == 200:
            data = response.json()["data"]
            
            print(f"Company: {data['company_name']}")
            print(f"Industry: {data['industry']}")
            print(f"Employees: {data['employee_count']}")
            print(f"Revenue: {data['financial_data']['revenue']}")
            
            # Display key personnel
            for person in data['key_personnel'][:3]:
                print(f"  {person['name']} - {person['position']}")
                
        else:
            error = response.json()["error"]
            print(f"Error: {error['message']}")
            print(f"Details: {error['details']}")

asyncio.run(extract_company())
```

#### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function extractCompany() {
  try {
    const response = await axios.post(
      'http://localhost:8000/api/v1/company/extract',
      {
        company_name: 'Airbnb',
        extraction_mode: 'comprehensive',
        include_contact_info: true,
        max_pages_to_crawl: 6
      },
      {
        timeout: 300000 // 5 minutes
      }
    );
    
    const { data } = response.data;
    
    console.log(`Company: ${data.company_name}`);
    console.log(`Industry: ${data.industry}`);
    console.log(`Founded: ${data.founded_year}`);
    console.log(`Headquarters: ${data.headquarters.city}, ${data.headquarters.state}`);
    
    // Display social media presence
    Object.entries(data.social_media)
      .filter(([platform, url]) => url)
      .forEach(([platform, url]) => {
        console.log(`${platform}: ${url}`);
      });
      
  } catch (error) {
    if (error.response) {
      const { error: apiError } = error.response.data;
      console.error(`API Error: ${apiError.message}`);
      console.error(`Details: ${apiError.details}`);
    } else {
      console.error(`Request Error: ${error.message}`);
    }
  }
}

extractCompany();
```

### Performance Considerations

1. **Extraction Mode Selection**: Choose the appropriate mode based on your needs
   - Use `basic` for quick validations
   - Use `standard` for most use cases
   - Use `comprehensive` only when detailed information is needed

2. **Caching**: Results are cached for 24 hours. Subsequent requests for the same company will be much faster.

3. **Batch Processing**: For multiple companies, use the [batch endpoint](./batch-processing.md) for better performance.

4. **Rate Limiting**: Respect rate limits to avoid throttling:
   - Maximum 5 concurrent extractions per IP
   - Maximum 100 requests per minute per IP

5. **Timeouts**: Set appropriate timeouts based on extraction mode:
   - Basic: 30-60 seconds
   - Standard: 60-120 seconds  
   - Comprehensive: 120-300 seconds

### Troubleshooting

#### Common Issues

1. **Company Not Found**
   - Verify company name spelling
   - Try providing domain parameter
   - Check if company has minimal web presence

2. **Timeout Errors**
   - Increase `timeout_seconds` parameter
   - Use `basic` mode for faster extraction
   - Check if company website is accessible

3. **Rate Limit Exceeded**
   - Reduce concurrent requests
   - Implement request queuing
   - Use batch processing for multiple companies

4. **Incomplete Data**
   - Try `comprehensive` mode for more data
   - Check if company has limited public information
   - Verify domain accessibility

#### Debug Information

Enable debug mode by setting `DEBUG=true` in environment variables for detailed logging and trace information.

### Related Endpoints

- [Batch Processing](./batch-processing.md) - Process multiple companies
- [Health Check](./health-check.md) - Service status
- [Extraction Scopes](./extraction-scopes.md) - Available extraction modes