# Company Search Agent - Technical Specification

## Overview

An intelligent agent system for discovering and analyzing VC-backed Indonesian startup companies using the Agno agents framework, GPT-5 mini via OpenRouter, and existing SERP/crawl infrastructure.

## Architecture Design

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Company Search Agent System                  │
├─────────────────────────────────────────────────────────────────┤
│  🤖 Agent Layer (Agno Framework + GPT-5 Mini via OpenRouter)   │
├─────────────────────────────────────────────────────────────────┤
│  🔍 Search Orchestration Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  📊 Data Processing & Enrichment Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Existing Infrastructure (SERP API + Crawl4ai)              │
└─────────────────────────────────────────────────────────────────┘
```

### Core Agents Architecture

#### 1. Master Orchestrator Agent
- **Role**: Coordinates all search activities and manages workflow
- **Model**: GPT-5 mini via OpenRouter
- **Responsibilities**:
  - Query planning and strategy selection
  - Agent task distribution and coordination
  - Result aggregation and deduplication
  - Progress monitoring and error handling

#### 2. VC Portfolio Discovery Agent
- **Role**: Specializes in VC portfolio website analysis
- **Target Sources**: East Ventures, AC Ventures, Alpha JWC, etc.
- **Capabilities**:
  - Portfolio page parsing and extraction
  - Company detail enrichment
  - VC relationship mapping

#### 3. Social Media Intelligence Agent
- **Role**: LinkedIn and Instagram company profile discovery
- **Specialized Knowledge**: Social platform patterns and structures
- **Capabilities**:
  - Profile validation and scoring
  - Social engagement analysis
  - Team size and growth indicators

#### 4. Directory Mining Agent
- **Role**: Startup database and directory exploration
- **Target Sources**: StartupIndonesia.co, Failory, Seedtable, Crunchbase
- **Capabilities**:
  - Directory navigation and data extraction
  - Cross-referencing and validation
  - Funding status verification

#### 5. Content Enrichment Agent
- **Role**: Deep content analysis and data enrichment
- **Capabilities**:
  - Website content analysis
  - Business model identification
  - Market positioning analysis
  - Competitive landscape mapping

#### 6. Validation and Scoring Agent
- **Role**: Data quality assurance and company scoring
- **Capabilities**:
  - Multi-source validation
  - Confidence scoring
  - Duplicate detection and merging
  - Quality assurance metrics

## Technical Implementation

### Agno Framework Integration

```python
# Core agent configuration
AGENT_CONFIG = {
    "framework": "agno",
    "model_provider": "openrouter",
    "model": "gpt-5-mini",
    "max_tokens": 4096,
    "temperature": 0.1,
    "timeout": 30000
}

# Agent definitions
class MasterOrchestratorAgent(AgnoAgent):
    role = "search_coordinator"
    expertise = ["query_planning", "result_aggregation", "workflow_management"]
    
class VCPortfolioAgent(AgnoAgent):
    role = "vc_portfolio_specialist"
    expertise = ["portfolio_analysis", "vc_relationship_mapping", "investment_tracking"]
    
class SocialMediaAgent(AgnoAgent):
    role = "social_intelligence"
    expertise = ["linkedin_analysis", "instagram_discovery", "social_validation"]
```

### OpenRouter GPT-5 Mini Configuration

```yaml
openrouter:
  base_url: "https://openrouter.ai/api/v1"
  model: "gpt-5-mini"
  api_key: "${OPENROUTER_API_KEY}"
  headers:
    HTTP-Referer: "http://localhost:8000"
    X-Title: "Indonesian Startup Discovery Agent"
  parameters:
    temperature: 0.1
    max_tokens: 4096
    top_p: 0.9
    frequency_penalty: 0.1
    presence_penalty: 0.1
```

### Integration with Existing Infrastructure

#### SERP API Integration Points

```python
# Enhanced search requests with agent intelligence
class AgentSearchRequest(SearchRequest):
    agent_context: Optional[Dict[str, Any]] = None
    search_strategy: Optional[str] = None
    priority_sources: Optional[List[str]] = None
    validation_level: Optional[int] = Field(default=3, ge=1, le=5)

# Agent-enhanced search endpoint
@router.post("/agent-search/companies")
async def agent_company_search(
    request: AgentSearchRequest,
    agent_orchestrator: MasterOrchestratorAgent = Depends(get_agent_orchestrator)
):
    """AI agent-powered company discovery with intelligent search strategies."""
    pass
```

#### Crawl API Integration

```python
# Agent-guided content extraction
class AgentCrawlRequest(CrawlRequest):
    analysis_focus: Optional[List[str]] = None  # ["funding", "team", "business_model"]
    agent_instructions: Optional[str] = None
    extraction_depth: Optional[int] = Field(default=2, ge=1, le=3)

@router.post("/agent-crawl/analyze")
async def agent_content_analysis(
    request: AgentCrawlRequest,
    content_agent: ContentEnrichmentAgent = Depends(get_content_agent)
):
    """AI agent-powered content analysis and business intelligence extraction."""
    pass
```

## Search Strategy Implementation

### Multi-Phase Discovery Workflow

#### Phase 1: Strategic Query Planning
```python
async def plan_discovery_strategy(
    orchestrator: MasterOrchestratorAgent,
    search_context: Dict[str, Any]
) -> SearchPlan:
    """
    Agent analyzes search context and creates optimal discovery plan
    
    Returns:
        SearchPlan with prioritized query sequences and resource allocation
    """
    planning_prompt = f"""
    Plan Indonesian startup discovery strategy:
    - Target: VC-backed companies in Indonesia
    - Context: {search_context}
    - Available resources: SERP API, Crawl4ai, social media access
    - Success metrics: 300-500 companies, 70%+ funding validation
    
    Create prioritized search plan with specific queries and expected outcomes.
    """
    
    plan = await orchestrator.plan(planning_prompt)
    return SearchPlan.parse_from_agent_response(plan)
```

#### Phase 2: Parallel Agent Execution
```python
async def execute_parallel_discovery(
    agents: Dict[str, AgnoAgent],
    search_plan: SearchPlan
) -> List[DiscoveryResult]:
    """
    Coordinate parallel agent execution for maximum efficiency
    """
    tasks = []
    
    # VC Portfolio Discovery (Highest Priority)
    if "vc_portfolio" in search_plan.phases:
        tasks.append(
            agents["vc_portfolio"].discover_portfolio_companies(
                vc_firms=["east_ventures", "ac_ventures", "alpha_jwc"],
                max_companies_per_vc=100
            )
        )
    
    # Social Media Discovery
    if "social_media" in search_plan.phases:
        tasks.append(
            agents["social_media"].discover_social_profiles(
                platforms=["linkedin", "instagram"],
                content_types=["companies", "accounts"],
                max_results_per_platform=200
            )
        )
    
    # Directory Mining
    if "directory_mining" in search_plan.phases:
        tasks.append(
            agents["directory"].mine_startup_directories(
                sources=["startupindonesia.co", "failory.com", "seedtable.com"],
                filters=["vc_funded", "active", "indonesia"]
            )
        )
    
    return await asyncio.gather(*tasks)
```

#### Phase 3: Content Enrichment and Validation
```python
async def enrich_and_validate_companies(
    companies: List[CompanyRecord],
    enrichment_agent: ContentEnrichmentAgent,
    validation_agent: ValidationAgent
) -> List[EnrichedCompanyRecord]:
    """
    Deep content analysis and multi-source validation
    """
    enriched_companies = []
    
    for company in companies:
        # Content enrichment
        if company.website:
            enriched_data = await enrichment_agent.analyze_company_website(
                url=company.website,
                focus_areas=["business_model", "funding_history", "team_info"]
            )
            company.enrich_with_website_data(enriched_data)
        
        # Multi-source validation
        validation_score = await validation_agent.validate_company(
            company=company,
            validation_sources=["linkedin", "crunchbase", "vc_websites"]
        )
        company.validation_score = validation_score
        
        if validation_score >= 0.7:  # High confidence threshold
            enriched_companies.append(company)
    
    return enriched_companies
```

### Query Templates and Agent Instructions

#### VC Portfolio Agent Queries
```python
VC_PORTFOLIO_INSTRUCTIONS = """
You are a VC portfolio analysis specialist. Your task is to discover and analyze 
portfolio companies from major Indonesian venture capital firms.

Key VCs to analyze:
1. East Ventures (300+ portfolio companies, most active in Indonesia)
2. AC Ventures (120+ companies, $500M+ AUM)  
3. Alpha JWC Ventures (70+ companies, $650M AUM)
4. Intudo Ventures (Indonesia-focused)
5. GDP Venture, Central Capital Ventura, Mandiri Capital

For each discovered company, extract:
- Company name and website
- Industry/sector focus
- Funding stage and amount (if available)
- Investment date
- VC investor details
- Current status (active/acquired/closed)

Use the following search strategies:
1. Direct portfolio page analysis (site:east.vc/portfolio)
2. VC press release mining
3. Portfolio company cross-referencing
4. Social media portfolio announcements

Quality requirements:
- Verify company is Indonesian or has significant Indonesian operations
- Confirm VC backing through multiple sources
- Prioritize companies with recent activity (2023-2024)
"""

SOCIAL_MEDIA_INSTRUCTIONS = """
You are a social media intelligence specialist focused on discovering Indonesian 
startup companies through LinkedIn and Instagram platforms.

LinkedIn Discovery Strategy:
- Target company profiles (linkedin.com/company/*)
- Look for Indonesian startups with 10+ employees
- Identify VC funding indicators in company descriptions
- Analyze company updates for funding announcements
- Cross-reference employee profiles for validation

Instagram Discovery Strategy:  
- Focus on business accounts with verified status
- Look for startup-related hashtags (#indonesiastartup, #jakartastartup)
- Identify funding announcement posts
- Analyze follower engagement for validation

For each discovered company, extract:
- Social media profile URLs
- Employee count indicators
- Funding status mentions
- Business model indicators
- Geographic location confirmation
- Engagement metrics and authenticity signals

Quality validation:
- Verify Indonesian presence through location tags/mentions
- Confirm business legitimacy through profile completeness
- Cross-reference with known VC portfolio companies
"""
```

## Data Models and Storage

### Enhanced Company Record Schema

```python
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field
from enum import Enum

class FundingStage(str, Enum):
    SEED = "seed"
    SERIES_A = "series_a"  
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    GROWTH = "growth"
    IPO = "ipo"
    UNKNOWN = "unknown"

class CompanyStatus(str, Enum):
    ACTIVE = "active"
    ACQUIRED = "acquired"
    CLOSED = "closed"
    UNKNOWN = "unknown"

class DiscoverySource(BaseModel):
    source_type: str  # "vc_portfolio", "linkedin", "directory", etc.
    source_url: HttpUrl
    discovery_date: datetime
    confidence_score: float = Field(ge=0.0, le=1.0)
    agent_id: str

class FundingRecord(BaseModel):
    stage: FundingStage
    amount: Optional[float] = None
    currency: str = "USD"
    date: Optional[datetime] = None
    investors: List[str] = []
    valuation: Optional[float] = None
    source: DiscoverySource

class SocialMediaProfile(BaseModel):
    platform: str  # "linkedin", "instagram"
    url: HttpUrl
    follower_count: Optional[int] = None
    verified: bool = False
    last_updated: Optional[datetime] = None
    engagement_score: Optional[float] = None

class EnrichedCompanyRecord(BaseModel):
    # Basic Information
    name: str
    website: Optional[HttpUrl] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    
    # Location
    country: str = "Indonesia"
    city: Optional[str] = None
    address: Optional[str] = None
    
    # Funding Information
    funding_stage: FundingStage = FundingStage.UNKNOWN
    total_funding: Optional[float] = None
    funding_history: List[FundingRecord] = []
    investors: List[str] = []
    
    # Company Status
    status: CompanyStatus = CompanyStatus.UNKNOWN
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    
    # Social Media Presence
    social_profiles: List[SocialMediaProfile] = []
    
    # Discovery Metadata
    discovery_sources: List[DiscoverySource] = []
    first_discovered: datetime
    last_updated: datetime
    
    # Validation Scores
    validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    funding_validation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    activity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Agent Analysis
    business_model: Optional[str] = None
    competitive_analysis: Optional[Dict[str, Any]] = None
    growth_indicators: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "TechStartup Indonesia",
                "website": "https://techstartup.id",
                "description": "Indonesian fintech startup providing digital payments",
                "industry": "Financial Technology",
                "sector": "Fintech",
                "city": "Jakarta",
                "funding_stage": "series_a",
                "total_funding": 5000000.0,
                "investors": ["East Ventures", "AC Ventures"],
                "employee_count": 50,
                "validation_score": 0.85,
                "social_profiles": [
                    {
                        "platform": "linkedin",
                        "url": "https://linkedin.com/company/techstartup-indonesia",
                        "follower_count": 5000,
                        "verified": True
                    }
                ]
            }
        }
    )
```

### API Response Models

```python
class CompanyDiscoveryResponse(BaseModel):
    """Response model for agent-powered company discovery."""
    
    query_context: Dict[str, Any]
    total_companies_discovered: int
    companies: List[EnrichedCompanyRecord]
    
    # Discovery Statistics
    discovery_stats: Dict[str, int]  # {"vc_portfolio": 150, "linkedin": 75, ...}
    validation_summary: Dict[str, float]  # {"avg_confidence": 0.78, ...}
    
    # Agent Execution Metadata
    agents_used: List[str]
    execution_time: float
    search_strategies_applied: List[str]
    
    # Quality Metrics
    high_confidence_companies: int  # validation_score >= 0.8
    funding_verified_companies: int
    active_companies: int
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
```

## Implementation Plan

### Phase 1: Foundation Setup (Week 1)
1. **Agno Framework Integration**
   - Set up Agno agents development environment
   - Configure OpenRouter GPT-5 mini connection
   - Create base agent classes and interfaces

2. **Enhanced API Endpoints**
   - Extend existing SERP/crawl endpoints with agent capabilities
   - Implement agent orchestration layer
   - Add company discovery specific routes

### Phase 2: Core Agent Development (Week 2-3)
1. **Master Orchestrator Agent**
   - Query planning and strategy selection logic
   - Multi-agent coordination and task distribution
   - Result aggregation and deduplication algorithms

2. **Specialized Discovery Agents**
   - VC Portfolio Discovery Agent implementation
   - Social Media Intelligence Agent development  
   - Directory Mining Agent creation
   - Content Enrichment Agent setup

### Phase 3: Integration and Testing (Week 4)
1. **System Integration**
   - Connect agents with existing SERP/crawl infrastructure
   - Implement data validation and scoring systems
   - Create comprehensive error handling and recovery

2. **Performance Optimization**
   - Parallel execution optimization
   - Caching strategies for agent responses
   - Rate limiting and API quota management

### Phase 4: Validation and Deployment (Week 5)
1. **Quality Assurance**
   - End-to-end testing with real Indonesian startup data
   - Validation accuracy testing and tuning
   - Performance benchmarking and optimization

2. **Documentation and Deployment**
   - API documentation and usage examples
   - Agent configuration and tuning guides
   - Production deployment and monitoring setup

## Success Metrics

### Quantitative Goals
- **Discovery Volume**: 300-500 VC-backed Indonesian companies
- **Validation Accuracy**: 70%+ funding status verification
- **Coverage Completeness**: 80%+ of major VC portfolios analyzed
- **Response Time**: <60 seconds for comprehensive company discovery
- **Cost Efficiency**: <$0.10 per validated company record

### Qualitative Goals
- **Data Quality**: Rich, structured company profiles with multiple validation sources
- **Agent Intelligence**: Smart query adaptation and strategy optimization
- **User Experience**: Simple API interface with comprehensive results
- **Scalability**: System handles 1000+ concurrent discovery requests

## Risk Assessment and Mitigation

### Technical Risks
1. **OpenRouter API Limits**: Implement intelligent rate limiting and fallback strategies
2. **Agent Response Quality**: Extensive prompt engineering and response validation
3. **Data Source Changes**: Monitoring and adaptive query strategies

### Business Risks  
1. **Cost Management**: Usage monitoring and budget controls
2. **Data Accuracy**: Multi-source validation and confidence scoring
3. **Legal Compliance**: Respect robots.txt and API terms of service

## Configuration and Environment

### Required Environment Variables
```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Agno Framework Configuration  
AGNO_ENVIRONMENT=production
AGNO_LOG_LEVEL=INFO
AGNO_MAX_AGENTS=10

# Agent Behavior Configuration
AGENT_MAX_TOKENS=4096
AGENT_TEMPERATURE=0.1
AGENT_TIMEOUT=30000
AGENT_RETRY_ATTEMPTS=3

# Discovery Configuration
MAX_COMPANIES_PER_SEARCH=500
VALIDATION_CONFIDENCE_THRESHOLD=0.7
PARALLEL_AGENT_LIMIT=5
```

### Dependencies
```toml
[dependencies]
# Existing dependencies...
agno = "^1.0.0"
openai = "^1.3.0"  # For OpenRouter compatibility
httpx = "^0.25.0"
redis = "^4.5.0"  # For caching and coordination
celery = "^5.3.0"  # For background agent tasks
```

This specification provides a comprehensive foundation for implementing the Indonesian startup discovery feature using intelligent agents while leveraging existing infrastructure efficiently.