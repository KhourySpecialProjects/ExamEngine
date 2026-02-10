from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage
    """

    # Core Application Settings
    app_name: str = "ExamEngine API"
    environment: str = "development"  # development, staging, production
    debug: bool = False

    # Database Configuration
    # no default value
    # Pydantic will look for DATABASE_URL in environment
    database_url: str = Field(description="PostgreSQL connection string")

    # AWS Configuration
    # LocalStack Support: Use endpoint_url for local development
    aws_endpoint_url: str | None = Field(
        default=None,
        description="AWS endpoint URL (use http://localstack:4566 for local dev with LocalStack)"
    )
    aws_access_key_id: str = Field(
        description="AWS access key (REQUIRED: use 'test' for LocalStack, real key for production)"
    )
    aws_secret_access_key: str = Field(
        description="AWS secret key (REQUIRED: use 'test' for LocalStack, real key for production)"
    )
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket"
    )
    aws_s3_bucket: str = Field(
        default="exam-engine-csvs",
        description="S3 bucket name for dataset storage"
    )

    # Security Settings
    secret_key: str = Field(description="Secret key for JWT token signing")
    algorithm: str = Field(default="HS256", description="Algorithm for JWT encoding")
    access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="JWT token expiration time in minutes",
    )

    # CORS Settings
    frontend_url: str = Field(
        default="http://localhost:3000", description="Frontend application URL for CORS"
    )

    # Database Connection Pool Settings
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Maximum overflow connections")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """
    Create  the settings instance.

    Returns:
        Settings instance
    """
    return Settings()
