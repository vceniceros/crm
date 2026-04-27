"""
Tests for POST /v1/auth/register

Fixtures:
  client      — FastAPI TestClient backed by in-memory SQLite
  db_session  — SQLAlchemy Session for direct DB assertions
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


_VALID_PAYLOAD = {
    "display_name": "Ana García",
    "email": "ana@example.com",
    "password": "securepass123",
    "recaptcha_token": "test-token",
}


@pytest.fixture(autouse=True)
def bypass_recaptcha():
    """Always bypass reCAPTCHA validation and rate-limiting in register tests."""
    with patch("src.api.auth.verify_recaptcha", new_callable=AsyncMock, return_value=0.9):
        yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the in-memory rate limiter state before each test."""
    from src.services.rate_limiter import rate_limiter
    rate_limiter.reset("register:testclient")
    yield
    rate_limiter.reset("register:testclient")


# ── Happy path ────────────────────────────────────────────────────────────────

def test_register_success(client: TestClient):
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock) as mock_email:
        response = client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 201
    assert response.json() == {"message": "Verification email sent"}
    mock_email.assert_awaited_once()
    call_kwargs = mock_email.await_args
    assert call_kwargs.args[0] == "ana@example.com"


def test_register_creates_pending_user(client: TestClient, db_session):
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    from sqlalchemy import select
    from src.models import User

    user = db_session.scalar(select(User).where(User.email == "ana@example.com"))
    assert user is not None
    assert user.status == "pending_verification"
    assert user.email_verified is False
    assert user.verification_token is not None
    assert user.verification_token_expires_at is not None


def test_register_email_send_failure_does_not_block(client: TestClient):
    """Registration succeeds even if the email fails to send."""
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock, side_effect=Exception("SMTP error")):
        response = client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 201


# ── Duplicate email ───────────────────────────────────────────────────────────

def test_register_duplicate_email(client: TestClient):
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    from src.services.rate_limiter import rate_limiter
    rate_limiter.reset("register:testclient")

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


# ── Validation ────────────────────────────────────────────────────────────────

def test_register_password_too_short(client: TestClient):
    payload = {**_VALID_PAYLOAD, "password": "short"}
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_invalid_email(client: TestClient):
    payload = {**_VALID_PAYLOAD, "email": "not-an-email"}
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_display_name_too_short(client: TestClient):
    payload = {**_VALID_PAYLOAD, "display_name": "X"}
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 422


# ── reCAPTCHA failure ─────────────────────────────────────────────────────────

def test_register_recaptcha_low_score(client: TestClient):
    with patch(
        "src.api.auth.verify_recaptcha",
        new_callable=AsyncMock,
        side_effect=ValueError("reCAPTCHA score too low."),
    ):
        response = client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    assert response.status_code == 422
    assert "recaptcha" in response.json()["detail"].lower()


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_register_rate_limit(client: TestClient):
    """6th request from the same IP within the hour must be rejected."""
    from src.services.rate_limiter import rate_limiter
    rate_limiter.reset("register:testclient")

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        for i in range(5):
            unique_email = f"user{i}@example.com"
            client.post("/v1/auth/register", json={**_VALID_PAYLOAD, "email": unique_email})

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/register", json={**_VALID_PAYLOAD, "email": "sixth@example.com"})

    assert response.status_code == 429


# ── user_type ─────────────────────────────────────────────────────────────────

def test_register_company_employee_sets_user_type(client: TestClient, db_session):
    """Registering as company_employee should persist user_type correctly."""
    payload = {**_VALID_PAYLOAD, "user_type": "company_employee"}
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/register", json=payload)

    assert response.status_code == 201

    from sqlalchemy import select
    from src.models import User

    user = db_session.scalar(select(User).where(User.email == "ana@example.com"))
    assert user is not None
    assert user.user_type == "company_employee"


def test_register_default_user_type_is_customer(client: TestClient, db_session):
    """When user_type is omitted, it defaults to 'customer'."""
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        client.post("/v1/auth/register", json=_VALID_PAYLOAD)

    from sqlalchemy import select
    from src.models import User

    user = db_session.scalar(select(User).where(User.email == "ana@example.com"))
    assert user is not None
    assert user.user_type == "customer"


def test_register_invalid_user_type_rejected(client: TestClient):
    """Invalid user_type values must return 422."""
    payload = {**_VALID_PAYLOAD, "user_type": "hacker"}
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 422
