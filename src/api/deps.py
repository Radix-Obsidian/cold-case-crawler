"""FastAPI dependencies for Cold Case Crawler API."""

from functools import lru_cache
from typing import Generator

from src.config import Settings, get_settings
from src.services.database import DatabaseService, create_database_service


def get_settings_dep() -> Settings:
    """Dependency for application settings."""
    return get_settings()


def get_database_service_dep() -> DatabaseService:
    """Dependency for database service."""
    return create_database_service()
