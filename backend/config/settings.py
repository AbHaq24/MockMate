
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MockMate API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Database URL will be configured when PostgreSQL is connected.
    database_url: str = ""

    # Groq uses the OpenAI-compatible SDK.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Authentication settings
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
