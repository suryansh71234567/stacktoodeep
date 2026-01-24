"""
Application Configuration using Pydantic Settings.

This module defines all configuration parameters for the Ride Optimization Platform.
Settings are loaded from environment variables, with sensible defaults for development.

Usage:
    from app.core.config import settings
    print(settings.DATABASE_URL)
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    For local development, create a .env file in the backend/ directory.
    """
    
    # =========================================================================
    # Application Settings
    # =========================================================================
    
    # Application name displayed in API docs and logs
    APP_NAME: str = "Ride Optimization Platform"
    
    # API version prefix (e.g., /api/v1/optimize)
    API_V1_PREFIX: str = "/api/v1"
    
    # Debug mode - enables detailed error messages and auto-reload
    # WARNING: Never enable in production!
    DEBUG: bool = False
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    
    # PostgreSQL connection URL
    # Format: postgresql+asyncpg://user:password@host:port/database
    # Using asyncpg driver for async support with SQLAlchemy 2.0
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ride_optimization"
    
    # Connection pool size - number of persistent connections to maintain
    # Increase for high-traffic production environments
    DB_POOL_SIZE: int = 5
    
    # Maximum overflow connections beyond pool_size
    # These are created when pool is exhausted, then closed when returned
    DB_MAX_OVERFLOW: int = 10
    
    # =========================================================================
    # Redis Configuration
    # =========================================================================
    
    # Redis connection URL for caching and rate limiting
    # Format: redis://[[username]:[password]@]host:port/db_number
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Cache TTL for optimization results (seconds)
    # Cached results expire after this duration
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    # =========================================================================
    # OSRM Routing API Configuration
    # =========================================================================
    
    # Base URL for OSRM (Open Source Routing Machine) API
    # Public demo server - replace with self-hosted for production
    # OSRM provides real road distances and durations for route optimization
    OSRM_BASE_URL: str = "http://router.project-osrm.org"
    
    # Timeout for OSRM API requests (seconds)
    # Increase if using distant or slow OSRM server
    OSRM_TIMEOUT_SECONDS: int = 10
    
    # =========================================================================
    # Optimization Parameters
    # =========================================================================
    
    # Maximum allowed detour time when pooling rides (minutes)
    # Riders won't be pooled if it adds more than this to their journey
    # Lower = stricter matching, higher = more pooling opportunities
    MAX_DETOUR_MINUTES: int = 15
    
    # Maximum passengers per vehicle for pooling
    # Includes driver capacity constraints
    MAX_PASSENGERS_PER_VEHICLE: int = 4
    
    # Timeout for optimization solver (seconds)
    # Prevents infinite loops on complex problems
    # Increase for larger batches, decrease for faster responses
    OPTIMIZATION_TIMEOUT_SECONDS: int = 30
    
    # Maximum pickup distance for pooling (kilometers)
    # Rides with pickups farther than this won't be pooled together
    MAX_PICKUP_DISTANCE_KM: float = 2.0
    
    # Time buffer overlap requirement (minutes)
    # Minimum overlap in time windows for rides to be poolable
    MIN_TIME_OVERLAP_MINUTES: int = 10
    
    # =========================================================================
    # Pricing Configuration
    # =========================================================================
    
    # Base fare for any ride (currency units)
    BASE_FARE: float = 50.0
    
    # Per-kilometer rate (currency units)
    PER_KM_RATE: float = 12.0
    
    # Per-minute rate for duration (currency units)
    PER_MINUTE_RATE: float = 2.0
    
    # Maximum discount percentage for flexible riders
    MAX_FLEXIBILITY_DISCOUNT_PERCENT: float = 40.0
    
    # =========================================================================
    # External API Keys (Optional)
    # =========================================================================
    
    # API key for premium mapping services (if used)
    MAPS_API_KEY: Optional[str] = None
    
    # =========================================================================
    # Pydantic Settings Configuration
    # =========================================================================
    
    model_config = SettingsConfigDict(
        # Load settings from .env file in backend/ directory
        env_file=".env",
        # .env file encoding
        env_file_encoding="utf-8",
        # Environment variables are case-insensitive
        case_sensitive=False,
        # Allow extra fields (for forward compatibility)
        extra="ignore"
    )


# Create a singleton settings instance
# Import this throughout the application: from app.core.config import settings
settings = Settings()
