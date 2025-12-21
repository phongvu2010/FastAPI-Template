from typing import Annotated, Any, List, Literal

from pydantic import AnyUrl, BeforeValidator, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_separated(v: Any) -> List[str] | str:
    """
    Parses origins from a comma-separated string.
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v

    raise ValueError(v)


class Settings(BaseSettings):
    """
    Manages application configuration and environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "SecureDocFlow API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Initial setup
    INITIAL_ADMIN_EMAIL: str

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Constructs the Async PostgreSQL DSN."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # CORS
    BACKEND_CORS_ORIGINS: Annotated[List[AnyUrl] | str, BeforeValidator(parse_comma_separated)] = []

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: AnyUrl

    # Security & Auth
    ALLOWED_EMAIL_DOMAINS: Annotated[List[str] | str, BeforeValidator(parse_comma_separated)] = []
    CSRF_SECRET_KEY: str
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = ENVIRONMENT != "local"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    @computed_field
    @property
    def COOKIE_MAX_AGE(self) -> int:
        """Calculates cookie max age in seconds."""
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60


# Initialize instance settings for use throughout the application.
settings = Settings()
