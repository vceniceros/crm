"""
Tests for company access management.

Covers:
  - AuthService.grant_company_access / revoke_company_access
  - GET  /v1/companies/{company_id}/members
  - POST /v1/companies/{company_id}/members
  - DELETE /v1/companies/{company_id}/members/{user_id}
  - Authorization enforcement (403 when caller lacks company_admin)
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Membership, Role, RoleAssignment, User
from src.models.company import Company
from src.security.passwords import hash_password
from src.services.auth_service import AuthService


# ── Test data helpers ─────────────────────────────────────────────────────────

def _create_user(db_session: Session, user_type: str = "company_employee", email: str | None = None) -> User:
    user = User(
        display_name="Test User",
        email=email or f"user-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        status="active",
        email_verified=True,
        user_type=user_type,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _grant_role_in_company(db_session: Session, user: User, company_id: str, role: Role) -> Membership:
    membership = Membership(
        user_id=user.user_id,
        tenant_type="company",
        tenant_id=company_id,
    )
    db_session.add(membership)
    db_session.flush()
    db_session.add(RoleAssignment(membership_id=membership.membership_id, role_id=role.role_id))
    db_session.commit()
    db_session.refresh(membership)
    return membership


# ── Service-level tests ───────────────────────────────────────────────────────

def test_grant_company_access_happy_path(db_session, seeded_roles, company):
    roles = seeded_roles
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee")

    svc = AuthService(db_session)
    membership = svc.grant_company_access(
        granting_admin_user_id=admin.user_id,
        target_user_id=target.user_id,
        company_id=company.company_id,
    )

    assert membership.tenant_type == "company"
    assert membership.tenant_id == company.company_id
    assert membership.user_id == target.user_id

    # Verify role assignment
    assignment = db_session.scalar(
        select(RoleAssignment).where(RoleAssignment.membership_id == membership.membership_id)
    )
    assert assignment is not None
    role = db_session.get(Role, assignment.role_id)
    assert role.role_name == "company_operator"


def test_grant_company_access_caller_not_admin(db_session, seeded_roles, company):
    # Caller only has company_operator, not company_admin
    caller = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, caller, company.company_id, seeded_roles["company_operator"])

    target = _create_user(db_session, user_type="company_employee")

    svc = AuthService(db_session)
    with pytest.raises(ValueError, match="company_admin"):
        svc.grant_company_access(
            granting_admin_user_id=caller.user_id,
            target_user_id=target.user_id,
            company_id=company.company_id,
        )


def test_grant_company_access_company_not_found(db_session, seeded_roles, company):
    # Grant caller company_admin role in existing company, but pass wrong company_id
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee")

    svc = AuthService(db_session)
    with pytest.raises(ValueError, match="not found"):
        svc.grant_company_access(
            granting_admin_user_id=admin.user_id,
            target_user_id=target.user_id,
            company_id="NONEXISTENT",
        )


def test_grant_company_access_already_has_access(db_session, seeded_roles, company):
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee")
    # Pre-grant access
    _grant_role_in_company(db_session, target, company.company_id, seeded_roles["company_operator"])

    svc = AuthService(db_session)
    with pytest.raises(ValueError, match="already has access"):
        svc.grant_company_access(
            granting_admin_user_id=admin.user_id,
            target_user_id=target.user_id,
            company_id=company.company_id,
        )


def test_revoke_company_access_happy_path(db_session, seeded_roles, company):
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee")
    membership = _grant_role_in_company(db_session, target, company.company_id, seeded_roles["company_operator"])
    membership_id = membership.membership_id

    svc = AuthService(db_session)
    svc.revoke_company_access(
        granting_admin_user_id=admin.user_id,
        target_user_id=target.user_id,
        company_id=company.company_id,
    )

    assert db_session.get(Membership, membership_id) is None
    assignments = db_session.scalars(
        select(RoleAssignment).where(RoleAssignment.membership_id == membership_id)
    ).all()
    assert len(assignments) == 0


# ── API-level tests ───────────────────────────────────────────────────────────

def _make_admin_headers(admin: User, company_id: str) -> dict:
    from tests.conftest import make_company_admin_token
    token = make_company_admin_token(admin.user_id, company_id)
    return {"Authorization": f"Bearer {token}"}


def _make_non_admin_headers(user: User, company_id: str) -> dict:
    from src.security.jwt import create_access_token
    membership = {
        "membership_id": str(uuid4()),
        "tenant_type": "company",
        "tenant_id": company_id,
        "roles": ["company_operator"],
    }
    token = create_access_token(user, membership)
    return {"Authorization": f"Bearer {token}"}


def test_api_list_members(client: TestClient, db_session: Session, seeded_roles, company):
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    member = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, member, company.company_id, seeded_roles["company_operator"])

    headers = _make_admin_headers(admin, company.company_id)
    response = client.get(f"/v1/companies/{company.company_id}/members", headers=headers)

    assert response.status_code == 200
    data = response.json()
    user_ids = [m["user_id"] for m in data]
    assert admin.user_id in user_ids
    assert member.user_id in user_ids


def test_api_grant_access(client: TestClient, db_session: Session, seeded_roles, company):
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee", email="newtarget@test.com")

    headers = _make_admin_headers(admin, company.company_id)
    response = client.post(
        f"/v1/companies/{company.company_id}/members",
        json={"user_email": target.email},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == target.user_id
    assert "company_operator" in data["roles"]


def test_api_revoke_access(client: TestClient, db_session: Session, seeded_roles, company):
    admin = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, admin, company.company_id, seeded_roles["company_admin"])

    target = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, target, company.company_id, seeded_roles["company_operator"])

    headers = _make_admin_headers(admin, company.company_id)
    response = client.delete(
        f"/v1/companies/{company.company_id}/members/{target.user_id}",
        headers=headers,
    )

    assert response.status_code == 204


def test_api_list_members_forbidden_without_admin_role(client: TestClient, db_session: Session, seeded_roles, company):
    operator = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, operator, company.company_id, seeded_roles["company_operator"])

    headers = _make_non_admin_headers(operator, company.company_id)
    response = client.get(f"/v1/companies/{company.company_id}/members", headers=headers)
    assert response.status_code == 403


def test_api_grant_access_forbidden_without_admin_role(client: TestClient, db_session: Session, seeded_roles, company):
    operator = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, operator, company.company_id, seeded_roles["company_operator"])

    headers = _make_non_admin_headers(operator, company.company_id)
    response = client.post(
        f"/v1/companies/{company.company_id}/members",
        json={"user_email": "someone@test.com"},
        headers=headers,
    )
    assert response.status_code == 403


def test_api_revoke_access_forbidden_without_admin_role(client: TestClient, db_session: Session, seeded_roles, company):
    operator = _create_user(db_session, user_type="company_employee")
    _grant_role_in_company(db_session, operator, company.company_id, seeded_roles["company_operator"])

    headers = _make_non_admin_headers(operator, company.company_id)
    response = client.delete(
        f"/v1/companies/{company.company_id}/members/some-user-id",
        headers=headers,
    )
    assert response.status_code == 403
