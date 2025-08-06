# Google SERP + Crawl4ai Integration - Simplified Spec

## Overview
Build a Google search system that combines Bright Data's SERP API with Crawl4ai's content extraction for enhanced search results.

## Core Features

### 1. Basic Search
- **Input**: Query, country, language, page
- **Output**: Standard Google SERP results
- **API**: `POST /api/search`

### 2. Enhanced Search  
- **Input**: Same as basic + extraction options
- **Output**: SERP results + extracted content (emails, phones, links)
- **API**: `POST /api/search/enhanced`

### 3. Content Analysis
- **Input**: Single URL
- **Output**: Deep content analysis
- **API**: `GET /api/analyze?url={url}`

## Architecture

```
Frontend → API Gateway → Search Service → [Bright Data SERP API]
                                      → [Crawl4ai Processor]
                                      → [Cache Layer]
```

## Data Flow

1. **Basic Search**: Query → Bright Data → Format → Return
2. **Enhanced Search**: Query → Bright Data → Crawl4ai extraction → Combine → Return
3. **Caching**: All results cached (1hr search, 24hr content)

## Tech Stack

- **Backend**: FastAPI/Python
- **Search**: Bright Data SERP API  
- **Content**: Crawl4ai AsyncWebCrawler
- **Cache**: Redis
- **Frontend**: React/Next.js (optional)

## API Examples

### Basic Search Request
```json
POST /api/search
{
  "query": "pizza restaurants",
  "country": "us",
  "language": "en",
  "page": 1
}
```

### Enhanced Search Request
```json
POST /api/search/enhanced  
{
  "query": "pizza restaurants",
  "country": "us",
  "language": "en", 
  "page": 1,
  "extract_contacts": true,
  "extract_media": true
}
```

### Response Format
```json
{
  "query": "pizza restaurants",
  "results_count": 1000000,
  "organic_results": [
    {
      "rank": 1,
      "title": "Best Pizza Place",
      "url": "https://example.com",
      "description": "Great pizza...",
      "extracted_content": {
        "emails": ["info@example.com"],
        "phones": ["+1-555-0123"],
        "social_links": ["https://twitter.com/pizza"]
      }
    }
  ]
}
```

## Implementation Plan

### Phase 1: Basic Search (2 weeks)
- [ ] Setup FastAPI project
- [ ] Integrate Bright Data SERP API  
- [ ] Basic search endpoint
- [ ] Response formatting

### Phase 2: Enhanced Search (2 weeks)  
- [ ] Setup Crawl4ai AsyncWebCrawler
- [ ] Content extraction pipeline
- [ ] Enhanced search endpoint
- [ ] Error handling

### Phase 3: Optimization (1 week)
- [ ] Redis caching layer
- [ ] Performance tuning
- [ ] Rate limiting
- [ ] Monitoring

### Phase 4: Frontend (2 weeks)
- [ ] React search interface
- [ ] Results display
- [ ] Export functionality

## Configuration

```bash
# Environment Variables
BRIGHT_DATA_CUSTOMER_ID=your_id
BRIGHT_DATA_ZONE_PASSWORD=your_password
REDIS_URL=redis://localhost:6379
API_PORT=8000
```

## Performance Targets

- **Basic Search**: < 2 seconds
- **Enhanced Search**: < 5 seconds  
- **Cache Hit Rate**: > 60%
- **Concurrent Users**: 50

This simplified spec focuses on the essential features and provides a clear implementation path.