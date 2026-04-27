"""
Tests for POST /v1/auth/verify-email
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.models import Membership, Role, RoleAssignment, User
from src.security.passwords import hash_password


def _make_pending_user(db_session, *, expired: bool = False, already_active: bool = False, user_type: str = "customer") -> User:
    token = str(uuid4())
    if expired:
        expires_at = datetime.now(UTC) - timedelta(hours=1)
    else:
        expires_at = datetime.now(UTC) + timedelta(hours=24)

    user = User(
        display_name="Test User",
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        status="active" if already_active else "pending_verification",
        email_verified=already_active,
        verification_token=None if already_active else token,
        verification_token_expires_at=None if already_active else expires_at,
        user_type=user_type,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Token error cases ─────────────────────────────────────────────────────────

def test_verify_email_invalid_token(client):
    response = client.post("/v1/auth/verify-email", json={"token": "nonexistent-token"})
    assert response.status_code == 422
    assert "invalid" in response.json()["detail"].lower()


def test_verify_email_expired_token(client, db_session):
    user = _make_pending_user(db_session, expired=True)
    response = client.post("/v1/auth/verify-email", json={"token": user.verification_token})
    assert response.status_code == 422


def test_verify_email_already_verified_token(client, db_session):
    """A token belonging to an already-active user must be rejected."""
    user = _make_pending_user(db_session, already_active=True)
    token = str(uuid4())
    user.verification_token = token
    user.verification_token_expires_at = datetime.now(UTC) + timedelta(hours=24)
    db_session.commit()

    user.status = "active"
    db_session.commit()

    response = client.post("/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 422


def test_verify_email_empty_token(client):
    response = client.post("/v1/auth/verify-email", json={"token": ""})
    assert response.status_code == 422


def test_verify_email_token_cannot_be_reused(client, db_session, seeded_roles):
    """Once verified (customer), the same token must be rejected on a second call."""
    user = _make_pending_user(db_session, user_type="customer")
    token = user.verification_token

    client.post("/v1/auth/verify-email", json={"token": token})
    response = client.post("/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 422


# ── Customer: auto-membership on verify ──────────────────────────────────────

def test_verify_email_customer_issues_tokens(client, db_session, seeded_roles):
    """Valid token for a customer should return tokens directly (single membership)."""
    user = _make_pending_user(db_session, user_type="customer")
    token = user.verification_token

    response = client.post("/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["requires_context_selection"] is False


def test_verify_email_activates_customer(client, db_session, seeded_roles):
    """Valid token should set status=active and clear token fields."""
    user = _make_pending_user(db_session, user_type="customer")
    token = user.verification_token

    client.post("/v1/auth/verify-email", json={"token": token})

    db_session.refresh(user)
    assert user.status == "active"
    assert user.email_verified is True
    assert user.verification_token is None
    assert user.verification_token_expires_at is None


def test_verify_email_customer_creates_membership_and_role(client, db_session, seeded_roles):
    """Customer verification must auto-create a membership + passenger_user role assignment."""
    from sqlalchemy import select

    user = _make_pending_user(db_session, user_type="customer")
    token = user.verification_token

    client.post("/v1/auth/verify-email", json={"token": token})

    membership = db_session.scalar(select(Membership).where(Membership.user_id == user.user_id))
    assert membership is not None
    assert membership.tenant_type == "customer"
    assert membership.tenant_id == "platform"

    assignment = db_session.scalar(
        select(RoleAssignment).where(RoleAssignment.membership_id == membership.membership_id)
    )
    assert assignment is not None

    role = db_session.get(Role, assignment.role_id)
    assert role is not None
    assert role.role_name == "passenger_user"


# ── Company employee: no membership on verify ─────────────────────────────────

def test_verify_email_company_employee_returns_access_pending(client, db_session):
    """Company employee gets access_pending response (no roles seeded needed)."""
    user = _make_pending_user(db_session, user_type="company_employee")
    token = user.verification_token

    response = client.post("/v1/auth/verify-email", json={"token": token})
    assert response.status_code == 200
    data = response.json()
    assert data.get("access_pending") is True
    assert data.get("user_type") == "company_employee"


def test_verify_email_company_employee_no_membership_created(client, db_session):
    """No membership row must exist for a company_employee after email verification."""
    from sqlalchemy import select

    user = _make_pending_user(db_session, user_type="company_employee")
    token = user.verification_token

    client.post("/v1/auth/verify-email", json={"token": token})

    membership = db_session.scalar(select(Membership).where(Membership.user_id == user.user_id))
    assert membership is None
