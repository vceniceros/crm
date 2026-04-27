import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Allow imports from the tests directory itself (for login_ticket_audit_runner)
sys.path.insert(0, str(Path(__file__).parent))

_SQLITE_URL = "sqlite:///:memory:"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "slow: marks tests that are intentionally slow (deselect with -m 'not slow')",
    )


# ── FastAPI TestClient fixtures (used by unit/integration tests) ──────────────

@pytest.fixture(scope="function")
def db_engine():
    """SQLite in-memory engine with the full schema.

    StaticPool ensures every connection reuses the same in-memory database,
    which is required for FastAPI's TestClient (which opens its own connections).
    """
    from src.db.base import Base

    engine = create_engine(
        _SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    TestSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, class_=Session)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    from src.db import get_db_session
    from src.main import app

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Phase 3 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def seeded_roles(db_session: Session):
    """Insert the core roles into the test DB."""
    from uuid import uuid4
    from src.models import Role

    role_names = ["passenger_user", "company_operator", "company_admin", "platform_admin", "ejecutivo"]
    roles = {}
    for name in role_names:
        role = Role(role_id=str(uuid4()), role_name=name)
        db_session.add(role)
        roles[name] = role
    db_session.commit()
    return roles


@pytest.fixture
def company(db_session: Session):
    """Insert a test Company row."""
    from src.models.company import Company

    c = Company(
        company_id="TESTCO",
        company_name="Test Company S.A.",
        logo_url=None,
        status="active",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def make_company_admin_token(user_id: str, company_id: str) -> str:
    """Create a JWT with company_admin role for the given user and company."""
    from src.security.jwt import create_access_token
    from src.models import User

    mock_user = type("_U", (), {"user_id": user_id, "email": "admin@test.com"})()
    membership = {
        "membership_id": "test-membership-id",
        "tenant_type": "company",
        "tenant_id": company_id,
        "roles": ["company_admin"],
    }
    return create_access_token(mock_user, membership)


# ── Phase 4 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def invitation(db_session: Session, company):
    """Insert a pending Invitation row for a test email + TESTCO."""
    import secrets
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4
    from src.models import Invitation, User
    from src.security.passwords import hash_password

    inviter = User(
        display_name="Platform Admin",
        email=f"pa-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass12345"),
        status="active",
        email_verified=True,
        user_type="company_employee",
    )
    db_session.add(inviter)
    db_session.flush()

    token = secrets.token_urlsafe(48)
    inv = Invitation(
        token=token,
        email="pending-invite@test.com",
        company_id=company.company_id,
        invited_by=inviter.user_id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(hours=48),
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return inv

