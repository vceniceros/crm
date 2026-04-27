"""
Tests for POST /v1/auth/forgot-password and POST /v1/auth/reset-password
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from src.models import User
from src.security.passwords import hash_password, verify_password


def _make_active_user(db_session, email: str = "reset@example.com", password: str = "password123") -> User:
    user = User(
        display_name="Reset User",
        email=email,
        password_hash=hash_password(password),
        status="active",
        email_verified=True,
        user_type="customer",
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

    keys = [
        "forgot-password:reset@example.com",
        "forgot-password:ghost@example.com",
        "forgot-password:inactive@example.com",
        "reset-password:testclient",
    ]
    for key in keys:
        rate_limiter.reset(key)
    yield
    for key in keys:
        rate_limiter.reset(key)


def test_forgot_password_returns_generic_message_and_sends_email(client, db_session):
    user = _make_active_user(db_session)

    with patch("src.api.auth.send_password_reset_email", new_callable=AsyncMock) as mock_email:
        response = client.post(
            "/v1/auth/forgot-password",
            json={"email": user.email, "recaptcha_token": "test-token"},
        )

    assert response.status_code == 200
    assert "active account exists" in response.json()["message"].lower()
    mock_email.assert_awaited_once()

    db_session.refresh(user)
    assert user.password_reset_token is not None
    assert user.password_reset_token_expires_at is not None


def test_forgot_password_unknown_email_returns_generic_message(client):
    with patch("src.api.auth.send_password_reset_email", new_callable=AsyncMock) as mock_email:
        response = client.post(
            "/v1/auth/forgot-password",
            json={"email": "ghost@example.com", "recaptcha_token": "test-token"},
        )

    assert response.status_code == 200
    mock_email.assert_not_awaited()


def test_forgot_password_ignores_inactive_user(client, db_session):
    db_session.add(
        User(
            display_name="Inactive User",
            email="inactive@example.com",
            password_hash=hash_password("password123"),
            status="pending_verification",
            email_verified=False,
            user_type="customer",
        )
    )
    db_session.commit()

    with patch("src.api.auth.send_password_reset_email", new_callable=AsyncMock) as mock_email:
        response = client.post(
            "/v1/auth/forgot-password",
            json={"email": "inactive@example.com", "recaptcha_token": "test-token"},
        )

    assert response.status_code == 200
    mock_email.assert_not_awaited()


def test_forgot_password_recaptcha_failure(client):
    with patch(
        "src.api.auth.verify_recaptcha",
        new_callable=AsyncMock,
        side_effect=ValueError("reCAPTCHA score too low."),
    ):
        response = client.post(
            "/v1/auth/forgot-password",
            json={"email": "reset@example.com", "recaptcha_token": "bad-token"},
        )

    assert response.status_code == 422


def test_reset_password_success(client, db_session):
    user = _make_active_user(db_session)
    user.password_reset_token = "valid-reset-token"
    user.password_reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=30)
    db_session.commit()

    response = client.post(
        "/v1/auth/reset-password",
        json={"token": "valid-reset-token", "new_password": "newpassword123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}

    refreshed = db_session.scalar(select(User).where(User.user_id == user.user_id))
    assert refreshed is not None
    assert refreshed.password_reset_token is None
    assert refreshed.password_reset_token_expires_at is None
    assert verify_password("newpassword123", refreshed.password_hash)


def test_reset_password_rejects_invalid_token(client):
    response = client.post(
        "/v1/auth/reset-password",
        json={"token": "missing-token", "new_password": "newpassword123"},
    )

    assert response.status_code == 422
    assert "invalid or expired" in response.json()["detail"].lower()


def test_reset_password_rejects_expired_token(client, db_session):
    user = _make_active_user(db_session)
    user.password_reset_token = "expired-token"
    user.password_reset_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/v1/auth/reset-password",
        json={"token": "expired-token", "new_password": "newpassword123"},
    )

    assert response.status_code == 422
    assert "invalid or expired" in response.json()["detail"].lower()


def test_reset_password_token_is_single_use(client, db_session):
    user = _make_active_user(db_session)
    user.password_reset_token = "single-use-token"
    user.password_reset_token_expires_at = datetime.now(UTC) + timedelta(minutes=30)
    db_session.commit()

    first = client.post(
        "/v1/auth/reset-password",
        json={"token": "single-use-token", "new_password": "newpassword123"},
    )
    second = client.post(
        "/v1/auth/reset-password",
        json={"token": "single-use-token", "new_password": "anotherpassword123"},
    )

    assert first.status_code == 200
    assert second.status_code == 422
