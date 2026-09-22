"""Application configuration, loaded from the environment (never hard-coded)."""
from functools import lru_cache
from typing import Annotated, ClassVar, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- Application ---
    APP_NAME: str = "E&J's CHICKENS"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # --- Database ---
    # A credential-free placeholder: real connection details belong in .env only,
    # never in source. `validate_for_runtime` refuses to start if it is unchanged.
    DATABASE_URL: str = "mysql+pymysql://USER:PASSWORD@localhost:3306/ej_chickens"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

    # --- Security ---
    JWT_SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # --- CORS ---
    # NoDecode: parsed by the validator below so a plain comma-separated string works.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- Farm defaults (overridable from the Settings module at runtime) ---
    DEFAULT_CURRENCY: str = "UGX"
    LOW_FEED_THRESHOLD_BAGS: int = 5
    HIGH_MORTALITY_RATE_PERCENT: float = 5.0
    BUDGET_WARNING_PERCENT: float = 80.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Accept either a JSON list or a comma-separated string from the env file."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    # ClassVar: a constant, not a configurable setting.
    DEFAULT_SECRET: ClassVar[str] = "change-me-in-production"
    PLACEHOLDER_DB_URL: ClassVar[str] = (
        "mysql+pymysql://USER:PASSWORD@localhost:3306/ej_chickens"
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"production", "prod"}

    @property
    def uses_default_secret(self) -> bool:
        return self.JWT_SECRET_KEY in (self.DEFAULT_SECRET, "", "CHANGE_ME_TO_A_LONG_RANDOM_STRING")

    @property
    def uses_placeholder_database(self) -> bool:
        return self.DATABASE_URL == self.PLACEHOLDER_DB_URL or "PASSWORD@" in self.DATABASE_URL

    def validate_for_runtime(self) -> None:
        """Refuse to start on placeholder configuration."""
        if self.uses_placeholder_database:
            raise RuntimeError(
                "DATABASE_URL is still the placeholder from the example configuration. "
                "Copy backend/.env.example to backend/.env and set your real MySQL "
                "connection string before starting the server."
            )
        if self.is_production and self.uses_default_secret:
            raise RuntimeError(
                "JWT_SECRET_KEY is still the default value. Set a long random key in .env "
                'before running in production: python -c "import secrets; '
                'print(secrets.token_urlsafe(64))"'
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
