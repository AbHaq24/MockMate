
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Check your .env file."
        )

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
    )


@lru_cache
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """Provide a database session to a FastAPI endpoint."""
    db = get_session_factory()()

    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Verify that PostgreSQL is reachable."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))

    return True
