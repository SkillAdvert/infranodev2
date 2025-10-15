"""Application configuration using Pydantic settings."""
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Central configuration for the application."""

    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    infra_cache_ttl: int = Field(default=600, env="INFRA_CACHE_TTL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
