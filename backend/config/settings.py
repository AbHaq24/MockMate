from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MockMate API"
    app_version: str = "0.1.0"
    environment: str = "development"
    rate_limit_enabled: bool = True

    database_url: str = ""

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000"

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Ensure PostgreSQL connection strings use psycopg (v3) dialect expected by SQLAlchemy 2."""
        if not v:
            return v
        cleaned = v.strip().strip("'\"")
        if cleaned.startswith("postgres://"):
            return "postgresql+psycopg://" + cleaned[len("postgres://"):]
        if cleaned.startswith("postgresql+psycopg2://"):
            return "postgresql+psycopg://" + cleaned[len("postgresql+psycopg2://"):]
        if cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
            return "postgresql+psycopg://" + cleaned[len("postgresql://"):]
        return cleaned

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return ["*"]
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
