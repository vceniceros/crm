"""
Tests for Phase 4 — Invitation acceptance flow.

Covers:
  - GET  /v1/invitations/{token} — valid pending → 200
  - GET  /v1/invitations/{token} — expired → 410
  - GET  /v1/invitations/{token} — unknown token → 404
  - POST /v1/invitations/{token}/accept — creates user, membership, role, returns tokens
  - POST /v1/invitations/{token}/accept — already accepted → 410
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import secrets


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_invitation(
    db_session,
    company,
    *,
    email: str = "invited@test.com",
    status: str = "pending",
    expires_delta: timedelta = timedelta(hours=48),
):
    from src.models import Invitation, User
    from src.security.passwords import hash_password

    # Need a real user as invited_by
    inviter = User(
        display_name="Inviter",
        email=f"inviter-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass12345"),
        status="active",
        email_verified=True,
        user_type="company_employee",
    )
    db_session.add(inviter)
    db_session.flush()

    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + expires_delta

    invitation = Invitation(
        token=token,
        email=email,
        company_id=company.company_id,
        invited_by=inviter.user_id,
        status=status,
        expires_at=expires_at,
    )
    db_session.add(invitation)
    db_session.commit()
    db_session.refresh(invitation)
    return invitation


# ── GET /v1/invitations/{token} ───────────────────────────────────────────────

def test_get_invitation_valid_pending_200(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company)

    response = client.get(f"/v1/invitations/{invitation.token}")
    assert response.status_code == 200
    data = response.json()
    assert data["invitation_id"] == invitation.invitation_id
    assert data["email"] == "invited@test.com"
    assert data["company_id"] == company.company_id
    assert data["company_name"] == company.company_name
    assert data["status"] == "pending"


def test_get_invitation_expired_410(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company, expires_delta=timedelta(hours=-1))

    response = client.get(f"/v1/invitations/{invitation.token}")
    assert response.status_code == 410


def test_get_invitation_unknown_token_404(client):
    response = client.get("/v1/invitations/TOTALLY-UNKNOWN-TOKEN")
    assert response.status_code == 404


def test_get_invitation_accepted_410(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company, status="accepted")

    response = client.get(f"/v1/invitations/{invitation.token}")
    assert response.status_code == 410


def test_get_invitation_revoked_410(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company, status="revoked")

    response = client.get(f"/v1/invitations/{invitation.token}")
    assert response.status_code == 410


# ── POST /v1/invitations/{token}/accept ──────────────────────────────────────

def test_accept_invitation_creates_user_and_returns_tokens(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company, email="newadmin@example.com")

    response = client.post(
        f"/v1/invitations/{invitation.token}/accept",
        json={"display_name": "New Admin", "password": "SecurePass1"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["requires_context_selection"] is False

    # Verify user was created
    from src.models import User, Membership, Role, RoleAssignment
    from sqlalchemy import select

    user = db_session.scalar(select(User).where(User.email == "newadmin@example.com"))
    assert user is not None
    assert user.status == "active"
    assert user.email_verified is True
    assert user.user_type == "company_employee"

    # Verify membership + company_admin role
    membership = db_session.scalar(
        select(Membership).where(
            Membership.user_id == user.user_id,
            Membership.tenant_type == "company",
            Membership.tenant_id == company.company_id,
        )
    )
    assert membership is not None

    admin_role = db_session.scalar(select(Role).where(Role.role_name == "company_admin"))
    assignment = db_session.scalar(
        select(RoleAssignment).where(
            RoleAssignment.membership_id == membership.membership_id,
            RoleAssignment.role_id == admin_role.role_id,
        )
    )
    assert assignment is not None

    # Verify invitation is marked accepted
    db_session.refresh(invitation)
    assert invitation.status == "accepted"
    assert invitation.accepted_at is not None


def test_accept_invitation_already_accepted_410(client, seeded_roles, company, db_session):
    invitation = _make_invitation(db_session, company, status="accepted")

    response = client.post(
        f"/v1/invitations/{invitation.token}/accept",
        json={"display_name": "User", "password": "SecurePass1"},
    )
    assert response.status_code == 410
