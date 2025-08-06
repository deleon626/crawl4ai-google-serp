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
    
    # FastAPI Configuration
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Crawl4ai Configuration
    crawl4ai_timeout: int = Field(default=30, env="CRAWL4AI_TIMEOUT")
    crawl4ai_max_retries: int = Field(default=3, env="CRAWL4AI_MAX_RETRIES")
    
    # API Configuration
    api_title: str = "Google SERP + Crawl4ai API"
    api_description: str = "API for Google SERP data retrieval and web crawling with Crawl4ai"
    api_version: str = "1.0.0"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()