"""Global Pytest fixtures and test database setup for Smart Basket."""

from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from scripts.seed import seed_database
from src.core.database import get_db
from src.main import app
from src.models.entities import Base
from src.models.fixtures import (
    CATEGORIES,
    PRICE_HISTORY,
    PRODUCTS,
    RETAILERS,
    STORE_PRICES,
    STORES,
)


@pytest.fixture(scope="session")
def test_engine():
    """Create an isolated in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def empty_db_session(test_engine) -> Generator[Session, None, None]:
    """Yield a clean database session with empty tables."""
    connection = test_engine.connect()
    transaction = connection.begin()
    test_session = sessionmaker(bind=connection, autocommit=False, autoflush=False)()

    yield test_session

    test_session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def db_session(empty_db_session: Session) -> Generator[Session, None, None]:
    """Yield a database session populated with supermarket catalog data."""
    seed_database(empty_db_session, reset=False)
    yield empty_db_session


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a FastAPI TestClient configured to use the test database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def raw_catalog_fixtures() -> dict[str, list[dict[str, Any]]]:
    """Provide structured raw catalog test fixtures for test assertions."""
    return {
        "retailers": RETAILERS,
        "stores": STORES,
        "categories": CATEGORIES,
        "products": PRODUCTS,
        "store_prices": STORE_PRICES,
        "price_history": PRICE_HISTORY,
    }
