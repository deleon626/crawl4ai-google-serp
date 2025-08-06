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
```

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment (copy .env.example to .env and configure)
cp .env.example .env
```

## Code Architecture

### FastAPI Application Structure
- **Main Entry**: `main.py` - FastAPI app with lifespan management, CORS, and centralized exception handling
- **Configuration**: `config/settings.py` - Pydantic Settings with environment variable loading
- **Routers**: HTTP endpoints organized by domain (`/api/v1/health`, `/api/v1/search`)
- **Services**: Business logic layer with async context managers for resource management
- **Models**: Pydantic v2 models for request/response validation with field validators
- **Clients**: External API integrations (Bright Data SERP API, future Crawl4ai)

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
- Field validators for country codes (2-letter uppercase) and language codes (2-letter lowercase)

### Client Integration Pattern
- **BrightDataClient**: HTTP client with retry logic, rate limiting, and connection pooling
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

### Environment Configuration
- Development: `.env` file with debug mode
- Production: Environment variables with secure defaults
- Settings validation through Pydantic with typed configuration

## Phase Development Status
**Phase 1**: Complete - Basic SERP search via Bright Data API
**Phase 2**: Planned - Crawl4ai integration for content extraction
**Phase 3**: Planned - Redis caching and performance optimization

## Important Notes
- Never commit sensitive data (API tokens are in .env files, not source)
- Always use async context managers for services to ensure proper resource cleanup
- Follow the existing error handling pattern - register handlers at app level, not router level
- Maintain backward compatibility when extending Pydantic models