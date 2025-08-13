# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Company Information Extraction API

**Production Ready System**: Enterprise-grade FastAPI application with intelligent company data extraction, batch processing, performance optimization, security hardening, and comprehensive monitoring.

## Development Commands

### Running the Application
```bash
# Start development server
python main.py
# Or with uvicorn
uvicorn main:app --reload

# Production mode with Gunicorn
gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --workers 4

# Docker production deployment
docker-compose -f deployment/docker-compose.prod.yml up -d
```

### Testing
```bash
# Run all tests
pytest

# Run with verbose output and coverage
pytest -v --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_company_integration.py -v
pytest tests/test_batch_processing.py -v
pytest tests/test_security_integration.py -v

# Run integration tests
python scripts/test_phase2_integration.py
python scripts/test_performance_optimizations.py

# Core company extraction tests
pytest tests/test_crawl4ai_client.py
pytest tests/test_bright_data.py
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

# Run company extraction examples
python examples/example_company_extraction.py
python examples/example_batch_processing.py
python examples/example_performance_testing.py

# Start web interfaces
streamlit run frontend/streamlit_app.py           # Single-page frontend
streamlit run frontend/streamlit_multipage_app.py # Multi-page frontend (radio buttons)
streamlit run frontend/🏠_Home.py                 # Native multipage frontend (recommended)
```

## Code Architecture

### FastAPI Application Structure
- **Main Entry**: `main.py` - FastAPI app with lifespan management, CORS, and centralized exception handling
- **Configuration**: `config/settings.py` - Pydantic Settings with environment variable loading
- **Routers**: HTTP endpoints organized by domain (`/api/v1/company`, `/api/v1/health`, `/api/v1/search`)
- **Services**: Business logic layer with async context managers for resource management
- **Models**: Pydantic v2 models for request/response validation with field validators
- **Clients**: External API integrations (Bright Data SERP API, Crawl4ai AsyncWebCrawler client)
- **Parsers**: HTML parsing for Google SERP results and company data extraction
- **Utils**: Shared utilities including caching, performance monitoring, security, and resource management

### Company Extraction Architecture
- **CompanyService**: Core extraction engine with multiple extraction modes
- **BatchCompanyService**: Batch processing with priority queuing and concurrent execution
- **ConcurrentExtraction**: Resource management and intelligent rate limiting
- **CompanyParser**: AI-powered data extraction with confidence scoring
- **CachingSystem**: Redis-based caching with 60-80% hit rates
- **PerformanceMonitoring**: Real-time metrics and automated optimization

### Service Architecture Pattern
Services use async context managers for proper resource management:
```python
async with CompanyService() as company_service:
    result = await company_service.extract_company(request)

# Batch processing with priority queuing
async with BatchCompanyService() as batch_service:
    batch_id = await batch_service.submit_batch(companies, mode="comprehensive")
```

### Error Handling Strategy
- **Centralized**: Exception handlers registered at app level in `main.py`
- **Hierarchical**: Specific errors (CompanyExtractionError) → Generic (ServiceError) → Fallback
- **Structured Responses**: Consistent JSON error format with error types and status codes
- **Graceful Degradation**: Fallback mechanisms for external service failures

### Data Models (Pydantic v2)
- **CompanyExtractionRequest/Response**: Core company extraction with multiple modes
- **BatchCompanyRequest/Response**: Multi-company processing with priority levels
- **CompanyData**: Comprehensive company information model with confidence scoring
- **ExtractionMetadata**: Processing metadata, performance metrics, and cache information
- **PerformanceMetrics**: Real-time performance tracking and optimization data
- Field validators for extraction modes, priority levels, and data quality validation

### Client Integration Pattern
- **BrightDataClient**: HTTP client with retry logic, rate limiting, and connection pooling
- **Crawl4aiClient**: AsyncWebCrawler wrapper with browser lifecycle management and timeout handling
- **CompanyParser**: AI-powered content extraction with confidence scoring
- **CachingClient**: Redis client with intelligent TTL management and cache warming
- **Resource Management**: Proper async context managers and connection cleanup

## Key Implementation Details

### Company Extraction Modes
- **Basic** (15-30s): Quick validation with essential company information
- **Standard** (30-60s): General research with comprehensive company data
- **Comprehensive** (45-90s): Due diligence with financial data and detailed analysis
- **Contact Focused** (20-40s): Sales prospecting with contact information priority
- **Financial Focused** (30-60s): Investment research with financial data priority

### Authentication & Security
- **API Key Authentication**: Token-based authentication with role-based access
- **Rate Limiting**: IP-based request throttling with intelligent backoff
- **Input Validation**: Comprehensive request validation and sanitization
- **Security Monitoring**: Intrusion detection and audit logging

### Performance Optimization
- **Advanced Caching**: Redis-based caching with intelligent TTL and cache warming
- **Concurrent Processing**: Resource-aware concurrent extraction with rate limiting
- **Batch Processing**: Priority queuing system with efficient resource allocation
- **Performance Monitoring**: Real-time metrics with automated optimization

### Async Patterns
All I/O operations use async/await with proper resource cleanup via context managers.

### Logging Strategy
Structured logging with operation decorators for request/response tracking and performance monitoring.

### Testing Approach
- Unit tests with mocked external dependencies
- Integration tests for API endpoints and company extraction workflows
- Performance tests for batch processing and concurrent operations
- Security tests for authentication and rate limiting
- End-to-end tests with real company extraction scenarios

### Environment Configuration
- Development: `.env` file with debug mode
- Production: Environment variables with secure defaults and monitoring
- Settings validation through Pydantic with typed configuration

## System Status
**Production Ready**: ✅ Complete enterprise-grade company information extraction system
- **Company Extraction Engine**: ✅ Multiple extraction modes with AI-powered parsing
- **Batch Processing**: ✅ Priority queuing with concurrent execution
- **Performance Optimization**: ✅ Advanced caching and resource management
- **Security Hardening**: ✅ Authentication, rate limiting, and monitoring
- **Comprehensive Monitoring**: ✅ Prometheus metrics, Grafana dashboards, alerting
- **Production Deployment**: ✅ Docker containers, CI/CD pipelines, automated deployment

## Project Structure

```
crawl4ai_GoogleSERP/
├── README.md                    # Main project documentation
├── CLAUDE.md                    # Claude Code instructions
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
├── pytest.ini                  # Test configuration
├── run.sh, run.bat             # Launch scripts
│
├── app/                        # Core application code
│   ├── clients/                # External API clients
│   │   ├── bright_data.py      # Google SERP API client
│   │   └── crawl4ai_client.py  # Web crawling client
│   ├── models/                 # Pydantic data models
│   │   ├── serp.py            # SERP data models
│   │   ├── crawl.py           # Crawling models
│   │   └── company.py         # Company extraction models
│   ├── parsers/                # HTML parsing utilities
│   │   ├── google_serp_parser.py # SERP result parsing
│   │   └── company_parser.py  # Company data extraction
│   ├── routers/                # FastAPI route handlers
│   │   ├── health.py          # System health checks
│   │   ├── search.py          # SERP search endpoints
│   │   ├── crawl.py           # Web crawling endpoints
│   │   ├── company.py         # Company extraction API
│   │   └── security.py        # Security and monitoring
│   ├── services/               # Business logic services
│   │   ├── serp_service.py    # SERP operations
│   │   ├── crawl_service.py   # Web crawling service
│   │   ├── company_service.py # Company extraction engine
│   │   ├── batch_company_service.py # Batch processing
│   │   └── concurrent_extraction.py # Concurrent processing
│   ├── utils/                  # Shared utilities
│   │   ├── caching.py         # Redis caching system
│   │   ├── performance.py     # Performance monitoring
│   │   ├── security.py        # Security utilities
│   │   └── resource_manager.py # Resource management
│   ├── monitoring/             # System monitoring
│   ├── security/               # Security implementation
│   └── compliance/             # Compliance and governance
│
├── config/                     # Configuration management
├── tests/                      # Comprehensive test suite
├── examples/                   # Company extraction usage examples
├── scripts/                    # Debug and utility scripts
├── frontend/                   # Streamlit web applications
├── docs/                       # Comprehensive documentation
│   ├── api/                   # API documentation
│   ├── deployment/            # Deployment guides
│   ├── user/                  # User guides
│   └── operations/            # Operational runbooks
├── deployment/                 # Production deployment
│   ├── docker-compose.prod.yml # Production stack
│   ├── Dockerfile.prod        # Production container
│   └── scripts/               # Deployment automation
└── .github/workflows/          # CI/CD automation
```

## Available Interfaces

### Web Interfaces
- **Native Multi-page**: `streamlit run frontend/🏠_Home.py` - Full multi-page app with sidebar navigation (recommended)
- **Single-page App**: `streamlit run frontend/streamlit_app.py` - Basic web UI for testing functionality
- **Multi-page App**: `streamlit run frontend/streamlit_multipage_app.py` - Enhanced UI with radio button navigation
- **Launcher Scripts**: `./run.sh` or `run.bat` - Start both backend and frontend simultaneously

### API Documentation
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **Alternative ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Company Extraction Endpoints
- **POST /api/v1/company/extract**: Extract single company information
- **POST /api/v1/company/batch/submit**: Submit batch extraction request
- **GET /api/v1/company/batch/{id}/status**: Get batch processing status
- **GET /api/v1/company/batch/{id}/results**: Get batch results
- **GET /api/v1/company/health**: Company service health check
- **GET /api/v1/company/batch/stats**: Batch processing statistics

### Core System Endpoints  
- **GET /api/v1/health**: Application health check with version info
- **GET /api/v1/health/detailed**: Detailed health check with dependencies
- **POST /api/v1/search**: Google SERP search via Bright Data API
- **POST /api/v1/crawl**: Web page crawling with Crawl4ai integration

## Development Guidelines

### Package Management
- **Preferred**: Use UV for faster dependency management (`uv pip install`, `uv run`)
- **Alternative**: Standard pip for compatibility when UV unavailable
- **Virtual Environment**: Use `.venv` directory (UV default) or `venv` (standard)

### Code Patterns
- **Services**: Always use async context managers for resource cleanup
- **Error Handling**: Register exception handlers at app level in `main.py`, not router level
- **Models**: Extend Pydantic models maintaining backward compatibility
- **Company Extraction**: Use CompanyService for consistent data extraction across the application
- **Caching**: Leverage Redis caching for performance optimization
- **Async Operations**: All I/O operations use async/await with proper resource management

### Testing Strategy
- **Unit Tests**: Mock external dependencies, focus on business logic
- **Integration Tests**: Test full API endpoints with real service interactions
- **Performance Tests**: Validate batch processing and concurrent operations
- **Security Tests**: Test authentication, rate limiting, and input validation
- **Test Files**: Follow pytest conventions (`test_*.py` in `tests/` directory)
- **Coverage**: Aim for comprehensive coverage with `pytest --cov=app`

### Deployment Strategy
- **Development**: Docker Compose with hot-reload capabilities
- **Production**: Multi-stage Docker builds with security hardening
- **CI/CD**: GitHub Actions with automated testing, security scanning, and deployment
- **Monitoring**: Comprehensive observability with Prometheus, Grafana, and ELK stack

## Important Notes
- Never commit sensitive data (API tokens are in .env files, not source)
- Configuration through environment variables with Pydantic Settings validation
- All external API calls include retry logic and proper error handling
- Structured logging with operation decorators for debugging and monitoring
- Redis caching is essential for production performance
- Security hardening enabled by default in production environments

## Key Configuration
- **Bright Data Token**: Set in environment variable `BRIGHT_DATA_TOKEN` (required)
- **Redis URL**: Set `REDIS_URL` for caching (required for production)
- **API Base URL**: Default `http://localhost:8000` for development
- **Default Zone**: `serp_api1` for Bright Data SERP API
- **Batch Processing**: Configure `MAX_CONCURRENT_EXTRACTIONS` and `BATCH_PROCESSING_ENABLED`
- **Security**: Set `API_KEY_REQUIRED=true` and `RATE_LIMITING_ENABLED=true` for production
- **Monitoring**: Configure `PERFORMANCE_MONITORING_ENABLED=true` and notification webhooks
- **Debug Mode**: Set `DEBUG=true` for development logging and detailed errors

## Performance Benchmarks
- **Basic Mode**: 15-30 seconds average response time
- **Standard Mode**: 30-60 seconds average response time
- **Comprehensive Mode**: 45-90 seconds average response time
- **Cache Hit**: < 1 second response time
- **Batch Processing**: 500-1000 companies/hour throughput
- **Concurrent Processing**: Up to 20 simultaneous extractions