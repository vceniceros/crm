"""Test fixtures for the CRM backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


TEST_DB_PATH = Path(__file__).parent / "test_microtv_crm.db"
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH.as_posix()}")
os.environ.setdefault("AUTH_JWT_SECRET", "change-me")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")
os.environ.setdefault("AUTH_JWT_ISSUER", "auth.microtv.ar")
os.environ.setdefault("AUTH_JWT_AUDIENCE", "microtv-platform")

from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.main import app
from crm_backend.db import Base, SessionLocal, engine
from crm_backend.db.bootstrap import initialize_database


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    """Reset the SQLite test database for each test.

    Yields:
        None: Control returns to the test.
    """

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        initialize_database(session)
    finally:
        session.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session for tests.

    Yields:
        Session: Active SQLAlchemy session.
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client.

    Yields:
        TestClient: FastAPI test client.
    """

    app.dependency_overrides.pop(get_auth_service_adapter, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
