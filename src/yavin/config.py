"""
Configuration management for Yavin.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # LLM Configuration
    # API_HOST: github, azure, openai
    api_host_llm: Literal["github", "azure", "openai"] = "github"
    
    # GitHub Models (free tier)
    github_token: str | None = None
    github_model: str = "gpt-4o"
    
    # Azure OpenAI
    azure_openai_endpoint: str | None = None
    azure_openai_chat_deployment: str | None = None
    azure_openai_version: str = "2024-02-15-preview"
    
    # OpenAI Direct
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "postgresql+asyncpg://yavin:yavin@localhost:5432/yavin"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Data Source API Keys
    domain_api_key: str | None = None
    newsapi_key: str | None = None

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
