# Company Information Extraction API - Examples

This directory contains comprehensive examples demonstrating how to use the Company Information Extraction API for various business scenarios. Each example is production-ready and includes error handling, logging, and best practices.

## 📋 Available Examples

### 🎯 Core Functionality Examples

#### `example_company_extraction.py`
Basic company extraction example showing single company data extraction with different modes.

**Features:**
- Single company extraction
- Different extraction modes (basic, standard, comprehensive)
- Error handling and validation
- Response data processing

**Usage:**
```bash
python examples/example_company_extraction.py
```

#### `example_batch_processing.py`
Comprehensive batch processing examples for handling multiple companies efficiently.

**Features:**
- Batch submission and monitoring
- Priority level management (normal, high, urgent)
- Progress tracking and status monitoring
- Error handling for failed extractions
- Multiple batch strategies

**Usage:**
```bash
python examples/example_batch_processing.py
```

**Example Scenarios:**
- Basic batch processing with standard mode
- High-priority comprehensive extraction
- Mixed-mode batches with different extraction types
- Error handling and retry logic

### 📊 Performance & Monitoring Examples

#### `example_performance_testing.py`
Production-ready performance testing suite for load testing and benchmarking.

**Features:**
- Single extraction performance testing
- Concurrent request handling
- Batch processing performance analysis
- System resource monitoring
- Response time analysis and reporting

**Usage:**
```bash
# Run full performance suite
python examples/example_performance_testing.py suite

# Run focused load test
python examples/example_performance_testing.py load

# Establish performance baseline
python examples/example_performance_testing.py baseline
```

**Metrics Tracked:**
- Response times (average, median, 95th percentile)
- Success/failure rates
- Requests per second
- System resource usage (CPU, memory)

#### `example_monitoring_production.py`
Production monitoring and health check system for operational environments.

**Features:**
- Comprehensive health checks (basic, detailed, service-specific)
- Performance metrics collection
- Alert condition monitoring
- Notification system integration (Slack, email)
- Data export and historical tracking

**Usage:**
```bash
# Single monitoring check
python examples/example_monitoring_production.py single

# Continuous monitoring
python examples/example_monitoring_production.py continuous

# Establish performance baseline
python examples/example_monitoring_production.py baseline
```

**Monitoring Capabilities:**
- API health status verification
- Response time monitoring with thresholds
- Error rate tracking and alerting
- Queue size monitoring
- System dependency health checks

### 🔗 Integration Examples

#### `example_integration_crm.py`
Complete CRM integration examples for Salesforce, HubSpot, and custom systems.

**Features:**
- Salesforce CRM integration with account creation/updates
- HubSpot CRM integration with company records
- Generic CSV/JSON export for CRM imports
- Lead enrichment and scoring workflows
- Data mapping and transformation utilities

**Usage:**
```bash
python examples/example_integration_crm.py
```

**Integration Patterns:**
- Lead qualification and enrichment
- Account/company record creation
- Data synchronization workflows
- Lead scoring algorithms
- Export formats for various CRM systems

#### `example_api_client_sdk.py`
Production-ready Python SDK with advanced features and error handling.

**Features:**
- Complete async/await SDK implementation
- Automatic retry logic with exponential backoff
- Rate limiting and caching support
- Comprehensive error handling and custom exceptions
- Batch processing with automatic waiting
- Configuration management and authentication

**Usage:**
```bash
python examples/example_api_client_sdk.py
```

**SDK Capabilities:**
- Single company extraction with all modes
- Batch processing with progress monitoring
- Bulk extraction with automatic batching
- Health checks and status monitoring
- Configurable timeouts and retry logic

### 🚀 Complete Workflow Examples

#### `example_complete_workflow.py`
End-to-end business intelligence workflows for real-world scenarios.

**Features:**
- Market research and competitive analysis
- Lead qualification and opportunity scoring
- Investment research and due diligence
- Intelligence report generation and export
- Executive summary creation

**Usage:**
```bash
python examples/example_complete_workflow.py
```

**Workflow Types:**
- **Market Research**: Industry analysis with competitor intelligence
- **Lead Qualification**: Prospect scoring and prioritization
- **Investment Research**: Financial analysis and risk assessment
- **Competitive Analysis**: Market positioning and opportunity identification

## 🛠️ Example Categories by Use Case

### Sales & Marketing
- `example_integration_crm.py` - Lead enrichment and CRM integration
- `example_complete_workflow.py` - Lead qualification workflow
- `example_batch_processing.py` - Prospect batch processing

### Investment & Finance
- `example_complete_workflow.py` - Investment research workflow
- `example_company_extraction.py` - Financial data extraction
- `example_api_client_sdk.py` - Systematic data collection

### Operations & DevOps
- `example_monitoring_production.py` - Production monitoring
- `example_performance_testing.py` - Performance validation
- `example_api_client_sdk.py` - Operational automation

### Data Analysis & Research
- `example_complete_workflow.py` - Market research workflow
- `example_batch_processing.py` - Large-scale data extraction
- `example_integration_crm.py` - Data export and transformation

## 📈 Performance Benchmarks

Based on the performance testing examples, typical benchmarks include:

### Response Times
- **Basic Mode**: 15-30 seconds average
- **Standard Mode**: 30-60 seconds average
- **Comprehensive Mode**: 45-90 seconds average
- **Cache Hit**: < 1 second response time

### Throughput
- **Single Extraction**: 100-200 companies/hour
- **Batch Processing**: 500-1000 companies/hour
- **Concurrent Processing**: Up to 20 simultaneous extractions

## 🔧 Configuration and Setup

### Environment Setup
```bash
# Install dependencies
pip install httpx asyncio psutil

# Set up environment variables
export API_BASE_URL="http://localhost:8000"
export BRIGHT_DATA_TOKEN="your_token_here"
```

### Example Configuration
Most examples support configuration through environment variables or configuration objects:

```python
# Basic configuration
API_BASE_URL = "http://localhost:8000"

# Advanced configuration (SDK)
config = SDKConfig(
    base_url="http://localhost:8000",
    timeout=300,
    max_retries=3,
    api_key="your_api_key",
    enable_caching=True
)
```

## 🚨 Error Handling Patterns

All examples implement comprehensive error handling:

### Common Error Types
- **APIError**: HTTP/API-related errors
- **ValidationError**: Input validation failures
- **RateLimitError**: Rate limiting exceeded
- **TimeoutError**: Request timeout scenarios
- **AuthenticationError**: Authentication failures

### Retry Strategies
- Exponential backoff for temporary failures
- Circuit breaker patterns for persistent issues
- Graceful degradation when services unavailable
- Intelligent error categorization and handling

## 📊 Data Export Formats

Examples support multiple export formats:

### JSON Export
```json
{
  "company_name": "OpenAI",
  "industry": "Artificial Intelligence",
  "financial_data": {
    "valuation": "$29 billion",
    "funding_raised": "$11.3 billion"
  }
}
```

### CSV Export
Flattened structure suitable for Excel and CRM imports.

### CRM-Specific Formats
- Salesforce account records
- HubSpot company objects
- Generic CRM import formats

## 🔍 Monitoring and Alerting

Production monitoring examples include:

### Health Check Types
- Basic API availability
- Detailed dependency checks
- Service-specific health validation
- End-to-end workflow verification

### Alert Conditions
- Response time thresholds (5s warning, 10s critical)
- Error rate thresholds (5% warning, 10% critical)
- Queue size monitoring (50 warning, 100 critical)
- System resource utilization

### Notification Channels
- Slack webhook integration
- Email notifications
- Log-based alerting
- Custom webhook support

## 📚 Best Practices Demonstrated

### Production Readiness
- Comprehensive error handling and recovery
- Logging and observability integration
- Configuration management and validation
- Resource management and cleanup

### Performance Optimization
- Async/await patterns for concurrency
- Intelligent batching and queuing
- Caching strategies and TTL management
- Rate limiting and backoff algorithms

### Security Considerations
- API key management and authentication
- Input validation and sanitization
- Secure communication patterns
- Audit logging and compliance

### Operational Excellence
- Health checks and monitoring
- Performance benchmarking and optimization
- Alert condition management
- Data export and backup strategies

## 🎯 Getting Started

1. **Start Simple**: Begin with `example_company_extraction.py` to understand basic functionality
2. **Scale Up**: Move to `example_batch_processing.py` for multiple companies
3. **Integrate**: Use `example_integration_crm.py` for CRM connectivity
4. **Optimize**: Implement `example_monitoring_production.py` for production monitoring
5. **Workflow**: Use `example_complete_workflow.py` for end-to-end business processes

## 🤝 Contributing

When adding new examples:
- Follow the established error handling patterns
- Include comprehensive logging and documentation
- Provide both basic and advanced usage scenarios
- Add configuration options for flexibility
- Include performance considerations and benchmarks

## 📞 Support

For questions about the examples:
- Check the main project documentation in `/docs`
- Review the API documentation at `/docs/api`
- Examine the integration guides at `/docs/user`
- Reference operational procedures at `/docs/operations`