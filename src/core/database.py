import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import DATABASE_URL


def get_sync_database_url(url: str | None = None) -> str:
    """Normalize and return synchronous database connection URL."""
    db_url = url or os.getenv("DATABASE_URL", DATABASE_URL)
    if db_url.startswith("postgresql+asyncpg://"):
        return db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if db_url.startswith("postgresql://") and not db_url.startswith(
        "postgresql+psycopg2://"
    ):
        return db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return db_url


sync_db_url = get_sync_database_url()
engine = create_engine(
    sync_db_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency provider yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
