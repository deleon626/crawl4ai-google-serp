# Technical Stack

## Backend Framework
application_framework: FastAPI 0.104+
database_system: Redis (caching only)
application_hosting: Self-hosted
deployment_solution: Docker (planned)

## Content Processing
web_crawling_framework: Crawl4ai AsyncWebCrawler
content_extraction: RegexExtractionStrategy, JsonCssExtractionStrategy for company/employee data
proxy_infrastructure: Bright Data SERP API
http_client: httpx with async connection pooling
employee_discovery: Web content analysis for company employee identification

## Data & Validation
data_models: Pydantic v2 with field validators
serialization: JSON with structured response formatting
caching_system: Redis with TTL management
validation_strategy: Input validation, country codes, language codes

## Development Tools
testing_framework: pytest with pytest-asyncio
test_coverage: 100% for implemented features (26 test cases)
code_quality: Python 3.8+ with type hints
error_handling: Comprehensive exception handling with HTTP status codes

## Prototyping & Development
prototyping_frontend: Streamlit with multi-page architecture for workflow navigation
streamlit_architecture: Multi-page application (Instagram → Company Analysis → Employee Discovery)
api_documentation: FastAPI auto-generated docs (/docs, /redoc)
development_server: uvicorn with auto-reload
environment_config: Pydantic Settings with .env file support

## External Integrations
search_api_provider: Bright Data SERP API with Bearer authentication
proxy_service: brd.superproxy.io with zone-based authentication
search_engine_target: Google Search with localization support
content_parsing: CSS selectors and regex patterns for data extraction

## Planned Integrations (Future)
database_hosting: n/a (module separation planned)
frontend_framework: n/a (separate development planned)
css_framework: n/a (no styling requirements)
ui_component_library: n/a (Streamlit sufficient for prototyping)
fonts_provider: n/a
icon_library: n/a
asset_hosting: n/a
code_repository_url: Local development
third_party_linkedin_api: ApiFy or similar for LinkedIn data enrichment (Phase 2.5+)

## Architecture Decisions
import_strategy: Standard Python imports with async/await patterns
session_management: Async context managers for resource cleanup
configuration_management: Environment-based with validation
logging_strategy: Structured logging with operation decorators
resource_management: Proper async cleanup and connection pooling