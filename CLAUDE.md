# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Start development server
python main.py
# Or with uvicorn
uvicorn main:app --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_search_api.py

# Run tests with coverage
pytest --cov=app

# Run specific test function
pytest tests/test_bright_data.py::TestBrightDataClient::test_search_success

# Phase 2 Integration Testing
python test_phase2_integration.py

# Phase 2.5 Integration Testing  
python test_phase25_integration.py

# Run individual test scripts
python test_direct_api.py
python test_parser.py
python test_pagination_accuracy.py
python test_indonesia_fashion.py
python test_batch_linkedin.py
python test_linkedin_queries.py

# New Phase 2 test files
pytest tests/test_crawl4ai_client.py
pytest tests/test_instagram_service.py  
pytest tests/test_link_validation_service.py
pytest tests/test_company_analysis_service.py
```

### Environment Setup
```bash
# Recommended: Use UV for faster dependency management
# Create virtual environment with UV
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with UV (faster)
uv pip install -r requirements.txt

# Alternative: Traditional Python setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment (copy .env.example to .env and configure)
cp .env.example .env

# Quick start with launcher scripts
./run.sh       # Unix/Linux/macOS - starts both backend and frontend
run.bat        # Windows - starts both backend and frontend

# Run examples
python example_search.py
python example_usage.py

# Start services individually
streamlit run streamlit_app.py                    # Frontend only
streamlit run streamlit_multipage_app.py          # Enhanced multipage frontend
```

## Code Architecture

### FastAPI Application Structure
- **Main Entry**: `main.py` - FastAPI app with lifespan management, CORS, and centralized exception handling
- **Configuration**: `config/settings.py` - Pydantic Settings with environment variable loading
- **Routers**: HTTP endpoints organized by domain (`/api/v1/health`, `/api/v1/search`)
- **Services**: Business logic layer with async context managers for resource management
- **Models**: Pydantic v2 models for request/response validation with field validators
- **Clients**: External API integrations (Bright Data SERP API, Crawl4ai AsyncWebCrawler client)
- **Parsers**: HTML parsing for Google SERP results with CSS selector-based extraction
- **Utils**: Shared utilities including custom exceptions, logging decorators, and pagination helpers

### Service Architecture Pattern
Services use async context managers for proper resource management:
```python
async with SERPService() as serp_service:
    result = await serp_service.search(request)
```

### Error Handling Strategy
- **Centralized**: Exception handlers registered at app level in `main.py`
- **Hierarchical**: Specific errors (BrightDataRateLimitError) → Generic (BrightDataError) → Fallback
- **Structured Responses**: Consistent JSON error format with error types and status codes

### Data Models (Pydantic v2)
- **SearchRequest/SearchResponse**: Core SERP functionality with field validation
- **BatchPaginationRequest/Response**: Multi-page search operations
- **PaginationMetadata**: Rich pagination state management
- **CrawlRequest/CrawlResponse**: Web crawling operations with Crawl4ai
- **InstagramAnalysisRequest/Response**: Instagram business profile analysis
- **InstagramSearchRequest/Response**: Instagram business search query generation
- **BusinessIndicators**: Business pattern detection with confidence scoring
- **LinkAnalysis**: Link extraction and validation results
- **KeywordExtraction**: Content keyword analysis with semantic grouping
- Field validators for country codes (2-letter uppercase) and language codes (2-letter lowercase)
- Advanced pagination with continuation tokens and metadata tracking

### Client Integration Pattern
- **BrightDataClient**: HTTP client with retry logic, rate limiting, and connection pooling
- **Crawl4aiClient**: AsyncWebCrawler wrapper with browser lifecycle management and timeout handling
- **GoogleSERPParser**: CSS selector-based HTML parsing for search results
- **InstagramSearchService**: Business-focused Instagram profile analysis with pattern recognition
- **LinkValidationService**: Link extraction and validation with business relevance scoring
- **KeywordExtractionService**: TF-IDF-based keyword extraction with semantic grouping
- **Resource Management**: Proper async context managers and connection cleanup
- **Error Translation**: API errors mapped to domain-specific exceptions

## Key Implementation Details

### Authentication
Bright Data API uses Bearer token authentication configured in environment variables.

### Async Patterns
All I/O operations use async/await with proper resource cleanup via context managers.

### Logging Strategy
Structured logging with operation decorators for request/response tracking and performance monitoring.

### Testing Approach
- Unit tests with mocked external dependencies
- Integration tests for API endpoints
- Comprehensive test coverage (26 test cases for Bright Data client)
- pytest with async support and short traceback format
- Dedicated test scripts for pagination accuracy and parser validation
- Example scripts demonstrating API usage patterns

### Environment Configuration
- Development: `.env` file with debug mode
- Production: Environment variables with secure defaults
- Settings validation through Pydantic with typed configuration

## Phase Development Status
**Phase 1**: ✅ Complete - Basic SERP search via Bright Data API with batch pagination
**Phase 2**: ✅ Complete - Intelligent Content Analysis with Crawl4ai integration, Instagram business analysis, and comprehensive content extraction
**Phase 2.5**: 🚧 In Progress - Company Analysis & Employee Discovery pipeline with LinkedIn integration  
**Phase 3**: Planned - Workflow Strategy Engine with parallel search execution
**Phase 4**: Planned - Redis caching and performance optimization

## Available Frontends
- **Streamlit App**: `streamlit run streamlit_app.py` - Interactive web UI for testing search functionality  
- **Multipage App**: `streamlit run streamlit_multipage_app.py` - Enhanced UI with multi-platform social media search
- **Launcher Scripts**: `./run.sh` or `run.bat` - Start both backend and frontend simultaneously
- **Example Scripts**: Direct API usage examples for development and testing
- **Integration Tests**: `python test_phase2_integration.py` - Comprehensive content analysis testing

## API Endpoints
### Core SERP Endpoints
- **GET /api/v1/health**: Application health check with version info
- **POST /api/v1/search**: Basic Google SERP search via Bright Data API
- **POST /api/v1/search/batch**: Batch pagination for multi-page searches

### Phase 2 Content Analysis Endpoints  
- **POST /api/v1/crawl**: Basic web crawling with Crawl4ai integration
- **GET /api/v1/crawl/test**: Health check endpoint for crawling functionality
- **POST /api/v1/analyze/instagram**: Comprehensive Instagram profile analysis with business indicators, link validation, and keyword extraction
- **POST /api/v1/search/instagram**: Generate optimized Instagram business search queries

### Phase 2.5 Company Analysis Endpoints
- **POST /api/v1/company/analyze**: Company profile analysis and employee discovery
- **POST /api/v1/company/search**: Generate optimized company search queries

## Development Guidelines

### Package Management
- **Preferred**: Use UV for faster dependency management (`uv pip install`, `uv run`)
- **Alternative**: Standard pip for compatibility when UV unavailable
- **Virtual Environment**: Use `.venv` directory (UV default) or `venv` (standard)

### Code Patterns
- **Services**: Always use async context managers for resource cleanup
- **Error Handling**: Register exception handlers at app level in `main.py`, not router level
- **Models**: Extend Pydantic models maintaining backward compatibility
- **Parsing**: Use GoogleSERPParser for consistent HTML parsing across the application
- **Pagination**: Handle continuation tokens and pagination metadata properly
- **Async Operations**: All I/O operations use async/await with proper resource management

### Testing Strategy
- **Unit Tests**: Mock external dependencies, focus on business logic
- **Integration Tests**: Test full API endpoints with real service interactions
- **Test Files**: Follow pytest conventions (`test_*.py` in `tests/` directory)
- **Coverage**: Aim for comprehensive coverage with `pytest --cov=app`
- **Phase Testing**: Use dedicated integration test scripts for multi-phase validation

## Important Notes
- Never commit sensitive data (API tokens are in .env files, not source)
- Configuration through environment variables with Pydantic Settings validation
- All external API calls include retry logic and proper error handling
- Structured logging with operation decorators for debugging and monitoring

## Key Configuration
- **Bright Data Token**: Set in environment variable `BRIGHT_DATA_TOKEN` (required)
- **API Base URL**: Default `http://localhost:8000` for development
- **Default Zone**: `serp_api1` for Bright Data SERP API
- **Timeouts**: 30 seconds default for both Bright Data and Crawl4ai operations
- **Debug Mode**: Set `DEBUG=true` for development logging and detailed errors