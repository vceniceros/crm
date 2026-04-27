"""
Tests for POST /v1/auth/resend-verification
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.models import User
from src.security.passwords import hash_password


def _make_pending_user(db_session, email: str = "pending@example.com") -> User:
    from datetime import UTC, datetime, timedelta

    user = User(
        display_name="Pending User",
        email=email,
        password_hash=hash_password("password123"),
        status="pending_verification",
        email_verified=False,
        verification_token=str(uuid4()),
        verification_token_expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def bypass_recaptcha():
    with patch("src.api.auth.verify_recaptcha", new_callable=AsyncMock, return_value=0.9):
        yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from src.services.rate_limiter import rate_limiter
    rate_limiter.reset("resend:pending@example.com")
    yield
    rate_limiter.reset("resend:pending@example.com")


_PAYLOAD = {"email": "pending@example.com", "recaptcha_token": "test-token"}


# ── Happy path ────────────────────────────────────────────────────────────────

def test_resend_verification_success(client, db_session):
    old_user = _make_pending_user(db_session)
    old_token = old_user.verification_token

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock) as mock_email:
        response = client.post("/v1/auth/resend-verification", json=_PAYLOAD)

    assert response.status_code == 200
    assert "verification" in response.json()["message"].lower()
    mock_email.assert_awaited_once()

    db_session.refresh(old_user)
    assert old_user.verification_token != old_token  # token was regenerated


# ── Silent success for unknown / verified emails ──────────────────────────────

def test_resend_nonexistent_email_returns_generic_message(client):
    """Must not reveal that the account doesn't exist."""
    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock) as mock_email:
        response = client.post("/v1/auth/resend-verification", json={**_PAYLOAD, "email": "ghost@example.com"})

    assert response.status_code == 200
    mock_email.assert_not_awaited()


def test_resend_already_active_email_returns_generic_message(client, db_session):
    user = User(
        display_name="Active User",
        email="active@example.com",
        password_hash=hash_password("pass"),
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock) as mock_email:
        response = client.post(
            "/v1/auth/resend-verification",
            json={"email": "active@example.com", "recaptcha_token": "token"},
        )

    assert response.status_code == 200
    mock_email.assert_not_awaited()


# ── reCAPTCHA failure ─────────────────────────────────────────────────────────

def test_resend_recaptcha_failure(client):
    with patch(
        "src.api.auth.verify_recaptcha",
        new_callable=AsyncMock,
        side_effect=ValueError("reCAPTCHA score too low."),
    ):
        response = client.post("/v1/auth/resend-verification", json=_PAYLOAD)

    assert response.status_code == 422


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_resend_rate_limit(client, db_session):
    _make_pending_user(db_session)
    from src.services.rate_limiter import rate_limiter
    rate_limiter.reset("resend:pending@example.com")

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        for _ in range(3):
            client.post("/v1/auth/resend-verification", json=_PAYLOAD)

    with patch("src.api.auth.send_verification_email", new_callable=AsyncMock):
        response = client.post("/v1/auth/resend-verification", json=_PAYLOAD)

    assert response.status_code == 429
