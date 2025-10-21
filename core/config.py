import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator



class Settings(BaseSettings):
    database_url: str = Field(..., description="Postgres connection string")
    db_pool_size: int = Field(10, description="Database connection pool size", ge=0)
    db_max_overflow: int = Field(20, description="Maximum overflow connections beyond pool_size", ge=0)

    # JWT

    jwt_secret_key: str = Field(..., description="secret key for JWT token signing", min_length=32)
    jwt_algorithm: str = Field("HS256", description="JWT signing algorithm")
    jwt_access_token_expires_minutes: int = Field(30, description="Access token expiration time in minutes", ge=1,
                                                  le=1440)
    jwt_refresh_token_expire_days: int = Field(7, description="Refresh token expiration time in days", ge=1, le=30)

    # redis
    redis_url: str | None = Field(None, description="Redis connection string for caching and Celery")

    # celery
    celery_broker_url: str | None = Field(None, description="Celery message broker URL (usually Redis)")
    celery_broker_backend: str | None = Field(None, description="Celery result backend URL")

    # cache TTL config
    cache_ttl_task_list: int = Field(60, description="Cache TTL for task lists in seconds", ge=0)
    cache_ttl_task_detail: int = Field(300,description="Cache TTL for individual task details in seconds",ge=0)
    cache_ttl_user_profile: int = Field(300, description="Cache TTL for user profiles in seconds", ge=0)

    #rate limiting
    rate_limit_per_minute: int = Field(100, description="maximum requests per minute per user", ge= 1)

    #app settings
    environment: str = Field("development", description="Application environment (development, staging, production)")
    debug: bool = Field(True, description="Enable debug mode (should be False in production)" )
    project_name : str = Field("Task Management API", description="Project name (shown in OpenAPI docs)")
    api_v1_prefix: str = Field("/api/v1", description= "API version 1 route prefix")

    #CORS config
    cors_origins: str = Field("http://localhost:3000,http://localhost:5173", description="Comma-separated list of allowed CORS origins")

    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    @field_validator('database_url')
    def validate_database_url(cls, v):
        #Ensure database URL is a valid PostgreSQL connection string
        if not v.startswith('postgresql://') and not v.startswith('postgresql+asyncpg://'):
            raise ValueError('DATABASE_URL must start with "postgresql://" or "postgresql+asyncpg://"')
        return v

    @field_validator('environment')
    def validate_environment(cls, v):
        #Ensure environment is one of the allowed values
        allowed = ['development', 'staging', 'production']
        if v.lower() not in allowed:
            raise ValueError(f'ENVIRONMENT must be one of: {", ".join(allowed)}')
        return v.lower()

    @field_validator('log_level')
    def validate_log_level(cls, v):
        #ensure log level is valid
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of: {", ".join(allowed)}')
        return v_upper

    @field_validator('jwt_secret_key')
    def validate_jwt_secret_strength(cls, v):
        # warn if JET secret is weak
        if len(v) < 32:
            raise ValueError( 'JWT_SECRET_KEY must be at least 32 characters for security')
        return v


    #helper properties
    @property
    def cors_origins_list(self) -> list[str]:
        #converts comm seperated cors to a list
        return [origin.strip() for origin in self.cors_origins.split(',')]

    @property
    def is_production(self)-> bool:
        #check if running in production environment
        return self.environment == "production"

    @property
    def is_development(self)-> bool:
        # check if running in production environment
        return self.environment == "development"

    @property
    def database_url_async(self) -> str:

        # Convert sync PostgreSQL URL to async (asyncpg driver).SQLAlchemy 2.0 with async requires asyncpg.

        if self.database_url.startswith('postgresql://'):
            return self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        return self.database_url



    class Config:
        project_root = Path(__file__).resolve().parent.parent
        env_file = project_root / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()




if __name__ == "__main__":
    print("✅ Configuration loaded successfully!")
    print(f"Database: {settings.database_url}")
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")
    print(f"JWT expiry: {settings.jwt_access_token_expires_minutes} minutes")
    print(f"Is production? {settings.is_production}")