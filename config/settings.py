"""Application configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Bright Data SERP API Configuration
    bright_data_api_url: str = Field(default="https://api.brightdata.com/request", env="BRIGHT_DATA_API_URL")
    bright_data_token: str = Field(default="52a735fae19e1eff8cb860522039a51d1a3da172af35106e7cb053f142065b43", env="BRIGHT_DATA_TOKEN")
    bright_data_zone: str = Field(default="serp_api1", env="BRIGHT_DATA_ZONE")
    bright_data_timeout: int = Field(default=30, env="BRIGHT_DATA_TIMEOUT")
    bright_data_max_retries: int = Field(default=3, env="BRIGHT_DATA_MAX_RETRIES")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=100, env="REDIS_MAX_CONNECTIONS")
    redis_retry_on_timeout: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")
    
    # FastAPI Configuration
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Crawl4ai Configuration
    crawl4ai_timeout: int = Field(default=30, env="CRAWL4AI_TIMEOUT")
    crawl4ai_max_retries: int = Field(default=3, env="CRAWL4AI_MAX_RETRIES")
    
    # Performance Configuration
    max_concurrent_extractions: int = Field(default=5, env="MAX_CONCURRENT_EXTRACTIONS")
    max_concurrent_searches: int = Field(default=10, env="MAX_CONCURRENT_SEARCHES")
    max_concurrent_crawls: int = Field(default=8, env="MAX_CONCURRENT_CRAWLS")
    batch_processing_enabled: bool = Field(default=True, env="BATCH_PROCESSING_ENABLED")
    max_concurrent_batches: int = Field(default=3, env="MAX_CONCURRENT_BATCHES")
    
    # Resource Management Configuration
    max_memory_mb: int = Field(default=512, env="MAX_MEMORY_MB")
    max_cpu_percent: float = Field(default=80.0, env="MAX_CPU_PERCENT")
    max_open_connections: int = Field(default=100, env="MAX_OPEN_CONNECTIONS")
    connection_pool_size: int = Field(default=20, env="CONNECTION_POOL_SIZE")
    connection_timeout: float = Field(default=30.0, env="CONNECTION_TIMEOUT")
    
    # Cache Configuration
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    company_cache_ttl: int = Field(default=86400, env="COMPANY_CACHE_TTL")  # 24 hours
    serp_cache_ttl: int = Field(default=21600, env="SERP_CACHE_TTL")  # 6 hours
    crawl_cache_ttl: int = Field(default=43200, env="CRAWL_CACHE_TTL")  # 12 hours
    
    # Rate Limiting Configuration
    search_rate_limit: float = Field(default=0.5, env="SEARCH_RATE_LIMIT")  # seconds between searches
    crawl_rate_limit: float = Field(default=1.0, env="CRAWL_RATE_LIMIT")  # seconds between crawls
    extraction_rate_limit: float = Field(default=2.0, env="EXTRACTION_RATE_LIMIT")  # seconds between extractions
    
    # Performance Monitoring Configuration
    performance_monitoring_enabled: bool = Field(default=True, env="PERFORMANCE_MONITORING_ENABLED")
    metrics_retention_hours: int = Field(default=24, env="METRICS_RETENTION_HOURS")
    performance_alert_threshold: float = Field(default=0.7, env="PERFORMANCE_ALERT_THRESHOLD")
    
    # Export Configuration
    export_directory: str = Field(default="exports", env="EXPORT_DIRECTORY")
    max_export_file_size_mb: int = Field(default=100, env="MAX_EXPORT_FILE_SIZE_MB")
    
    # Security Configuration
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    require_https: bool = Field(default=True, env="REQUIRE_HTTPS")
    enable_security_headers: bool = Field(default=True, env="ENABLE_SECURITY_HEADERS")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    max_requests_per_minute: int = Field(default=60, env="MAX_REQUESTS_PER_MINUTE")
    security_log_level: str = Field(default="WARNING", env="SECURITY_LOG_LEVEL")
    
    # GDPR Compliance Configuration
    enable_gdpr_compliance: bool = Field(default=True, env="ENABLE_GDPR_COMPLIANCE")
    data_retention_days: int = Field(default=365, env="DATA_RETENTION_DAYS")
    audit_log_retention_days: int = Field(default=2555, env="AUDIT_LOG_RETENTION_DAYS")  # 7 years
    enable_consent_tracking: bool = Field(default=True, env="ENABLE_CONSENT_TRACKING")
    
    # Robots.txt Compliance Configuration
    enable_robots_compliance: bool = Field(default=True, env="ENABLE_ROBOTS_COMPLIANCE")
    min_crawl_delay_seconds: float = Field(default=1.0, env="MIN_CRAWL_DELAY_SECONDS")
    max_requests_per_domain_hour: int = Field(default=100, env="MAX_REQUESTS_PER_DOMAIN_HOUR")
    respect_crawl_delay: bool = Field(default=True, env="RESPECT_CRAWL_DELAY")
    
    # Production Monitoring Configuration
    enable_production_monitoring: bool = Field(default=True, env="ENABLE_PRODUCTION_MONITORING")
    monitoring_collection_interval: int = Field(default=30, env="MONITORING_COLLECTION_INTERVAL")
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    sla_availability_target: float = Field(default=99.9, env="SLA_AVAILABILITY_TARGET")
    sla_response_time_ms: int = Field(default=1000, env="SLA_RESPONSE_TIME_MS")
    
    # API Configuration
    api_title: str = "Google SERP + Crawl4ai API"
    api_description: str = "Enterprise-grade API for Google SERP data retrieval and web crawling with comprehensive security, compliance, and monitoring"
    api_version: str = "2.0.0-enterprise"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()