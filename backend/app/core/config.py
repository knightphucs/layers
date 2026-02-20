"""
LAYERS - Application Configuration
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App
    app_name: str = "LAYERS"
    app_version: str = "0.1.0"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    
    # Database
    database_url: str = "postgresql+asyncpg://layers_user:layers_secret_2024@localhost:5432/layers_db"
    database_url_sync: str = "postgresql://layers_user:layers_secret_2024@localhost:5432/layers_db"
    test_database_url: str = "postgresql+asyncpg://layers_user:layers_secret_2024@localhost:5432/layers_test_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret_key: str = "jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "layers_minio"
    minio_secret_key: str = "layers_minio_secret"
    minio_bucket_name: str = "layers-files"
    minio_secure: bool = False
    
    # Firebase
    firebase_credentials_path: Optional[str] = None
    
    # Geo Settings
    default_nearby_radius: int = 1000  # meters
    geo_lock_radius: int = 50  # meters
    max_speed_mps: int = 1389  # meters per second (anti-cheat)
    
    # Rate Limits
    artifacts_per_day: int = 3
    min_distance_between_artifacts: int = 20  # meters
    
    # Slow Mail
    slow_mail_min_delay_hours: int = 6
    slow_mail_max_delay_hours: int = 12
    
    # Additional passwords (used by docker-compose)
    postgres_password: Optional[str] = None
    redis_password: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use dependency injection: settings = Depends(get_settings)
    """
    return Settings()


# Quick access
settings = get_settings()
