"""
Tests for Phase 4 — AdminService and /v1/admin/* endpoints.

Covers:
  Service-level:
  - create_company happy path
  - create_company duplicate → ValueError
  - assign_or_invite_company_admin — unregistered email → Invitation created
  - assign_or_invite_company_admin — existing company_employee → assigned
  - assign_or_invite_company_admin — existing company_admin elsewhere, force=False → ConflictError
  - assign_or_invite_company_admin — same conflict, force=True → assigned
  - assign_or_invite_company_admin — already admin of this company → ValueError
  - assign_or_invite_company_admin — customer email → ValueError
  - revoke_company_admin happy path — role + membership deleted
  - revoke_company_admin — membership kept when other role assignment exists

  API-level:
  - POST /v1/admin/companies — 201
  - POST /v1/admin/companies — 403 without platform_admin
  - POST /v1/admin/companies/{id}/admins — 202 (Caso B)
  - POST /v1/admin/companies/{id}/admins — 201 (Caso A)
  - POST /v1/admin/companies/{id}/admins — 409 conflict, force=False
  - POST /v1/admin/companies/{id}/admins?force=true — 201
  - DELETE /v1/admin/companies/{id}/admins/{uid} — 204
  - GET /v1/admin/companies/{id}/admins — returns list
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Invitation, Membership, Role, RoleAssignment, User
from src.models.company import Company
from src.security.passwords import hash_password
from src.services.admin_service import AdminService, ConflictError


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_user(
    db_session: Session,
    *,
    user_type: str = "company_employee",
    email: str | None = None,
    status: str = "active",
) -> User:
    user = User(
        display_name="Test User",
        email=email or f"user-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        status=status,
        email_verified=True,
        user_type=user_type,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _grant_role(
    db_session: Session,
    user: User,
    company_id: str,
    role: Role,
) -> Membership:
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


def _make_platform_admin_token(user_id: str) -> str:
    from src.security.jwt import create_access_token
    from types import SimpleNamespace

    fake_user = SimpleNamespace(user_id=user_id, email="admin@test.com")
    return create_access_token(
        fake_user,
        {
            "membership_id": str(uuid4()),
            "tenant_type": "platform",
            "tenant_id": "platform",
            "roles": ["platform_admin"],
        },
    )


def _make_company_admin_token(user_id: str, company_id: str) -> str:
    from src.security.jwt import create_access_token
    from types import SimpleNamespace

    fake_user = SimpleNamespace(user_id=user_id, email="ca@test.com")
    return create_access_token(
        fake_user,
        {
            "membership_id": str(uuid4()),
            "tenant_type": "company",
            "tenant_id": company_id,
            "roles": ["company_admin"],
        },
    )


# ── Service-level tests ───────────────────────────────────────────────────────

def test_create_company_happy_path(db_session):
    svc = AdminService(db_session)
    company = svc.create_company("NEWCO", "New Company S.A.", None)
    assert company.company_id == "NEWCO"
    assert company.status == "active"


def test_create_company_duplicate_raises(db_session, company):
    svc = AdminService(db_session)
    with pytest.raises(ValueError, match="already exists"):
        svc.create_company(company.company_id, "Other Name", None)


def test_assign_invite_unregistered_email_creates_invitation(db_session, seeded_roles, company):
    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    result = svc.assign_or_invite_company_admin(
        company_id=company.company_id,
        user_email="newadmin@notregistered.com",
        invited_by_user_id=platform_admin.user_id,
        force=False,
    )

    assert result["status"] == "invited"
    assert result["invitation_id"] is not None

    invitation = db_session.get(Invitation, result["invitation_id"])
    assert invitation is not None
    assert invitation.email == "newadmin@notregistered.com"
    assert invitation.status == "pending"
    # expires_at ≈ now + 48h
    delta = invitation.expires_at.replace(tzinfo=UTC) - datetime.now(UTC)
    assert timedelta(hours=47) < delta < timedelta(hours=49)


def test_assign_existing_company_employee_assigns_directly(db_session, seeded_roles, company):
    target = _create_user(db_session, user_type="company_employee")
    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    result = svc.assign_or_invite_company_admin(
        company_id=company.company_id,
        user_email=target.email,
        invited_by_user_id=platform_admin.user_id,
        force=False,
    )

    assert result["status"] == "assigned"
    assert result["user_id"] == target.user_id

    # Verify role assignment was created
    membership = db_session.scalar(
        select(Membership).where(
            Membership.user_id == target.user_id,
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


def test_assign_existing_admin_elsewhere_force_false_raises_conflict(db_session, seeded_roles, company):
    # Create second company for conflict
    other_company = Company(company_id="OTHERCO", company_name="Other Co", status="active")
    db_session.add(other_company)
    db_session.commit()

    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, "OTHERCO", seeded_roles["company_admin"])

    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    with pytest.raises(ConflictError) as exc_info:
        svc.assign_or_invite_company_admin(
            company_id=company.company_id,
            user_email=target.email,
            invited_by_user_id=platform_admin.user_id,
            force=False,
        )

    assert any(c.company_id == "OTHERCO" for c in exc_info.value.companies)


def test_assign_existing_admin_elsewhere_force_true_succeeds(db_session, seeded_roles, company):
    other_company = Company(company_id="OTHERCO2", company_name="Other Co 2", status="active")
    db_session.add(other_company)
    db_session.commit()

    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, "OTHERCO2", seeded_roles["company_admin"])

    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    result = svc.assign_or_invite_company_admin(
        company_id=company.company_id,
        user_email=target.email,
        invited_by_user_id=platform_admin.user_id,
        force=True,
    )

    assert result["status"] == "assigned"


def test_assign_already_admin_of_this_company_raises(db_session, seeded_roles, company):
    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, company.company_id, seeded_roles["company_admin"])

    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    with pytest.raises(ValueError, match="already company_admin"):
        svc.assign_or_invite_company_admin(
            company_id=company.company_id,
            user_email=target.email,
            invited_by_user_id=platform_admin.user_id,
            force=False,
        )


def test_assign_customer_email_raises(db_session, seeded_roles, company):
    customer = _create_user(db_session, user_type="customer")
    platform_admin = _create_user(db_session, user_type="company_employee")
    svc = AdminService(db_session)

    with pytest.raises(ValueError, match="customer"):
        svc.assign_or_invite_company_admin(
            company_id=company.company_id,
            user_email=customer.email,
            invited_by_user_id=platform_admin.user_id,
            force=False,
        )


def test_revoke_company_admin_deletes_membership_when_no_other_roles(db_session, seeded_roles, company):
    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, company.company_id, seeded_roles["company_admin"])

    svc = AdminService(db_session)
    svc.revoke_company_admin(user_id=target.user_id, company_id=company.company_id)

    membership = db_session.scalar(
        select(Membership).where(
            Membership.user_id == target.user_id,
            Membership.tenant_id == company.company_id,
        )
    )
    assert membership is None


def test_revoke_company_admin_keeps_membership_if_other_roles_exist(db_session, seeded_roles, company):
    target = _create_user(db_session, user_type="company_employee")
    membership = _grant_role(db_session, target, company.company_id, seeded_roles["company_admin"])

    # Add a second role to the same membership
    db_session.add(
        RoleAssignment(
            membership_id=membership.membership_id,
            role_id=seeded_roles["company_operator"].role_id,
        )
    )
    db_session.commit()

    svc = AdminService(db_session)
    svc.revoke_company_admin(user_id=target.user_id, company_id=company.company_id)

    # Membership must still exist
    surviving = db_session.scalar(
        select(Membership).where(Membership.membership_id == membership.membership_id)
    )
    assert surviving is not None

    # Only company_admin role should be gone
    admin_role = seeded_roles["company_admin"]
    admin_assignment = db_session.scalar(
        select(RoleAssignment).where(
            RoleAssignment.membership_id == membership.membership_id,
            RoleAssignment.role_id == admin_role.role_id,
        )
    )
    assert admin_assignment is None


# ── API-level tests ───────────────────────────────────────────────────────────

def test_api_create_company_201(client, seeded_roles):
    token = _make_platform_admin_token(str(uuid4()))
    response = client.post(
        "/v1/admin/companies",
        json={"company_id": "APITEST", "company_name": "API Test Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_id"] == "APITEST"
    assert data["status"] == "active"


def test_api_create_company_403_without_platform_admin(client, seeded_roles, company):
    non_admin_id = str(uuid4())
    token = _make_company_admin_token(non_admin_id, company.company_id)
    response = client.post(
        "/v1/admin/companies",
        json={"company_id": "BLOCKED", "company_name": "Blocked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_api_assign_admin_caso_b_202(client, seeded_roles, company):
    token = _make_platform_admin_token(str(uuid4()))
    response = client.post(
        f"/v1/admin/companies/{company.company_id}/admins",
        json={"user_email": "casob@noemail.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "invited"
    assert data["invitation_id"] is not None


def test_api_assign_admin_caso_a_201(client, seeded_roles, company, db_session):
    target = _create_user(db_session, user_type="company_employee")
    token = _make_platform_admin_token(str(uuid4()))
    response = client.post(
        f"/v1/admin/companies/{company.company_id}/admins",
        json={"user_email": target.email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "assigned"
    assert data["user_id"] == target.user_id


def test_api_assign_admin_409_conflict(client, seeded_roles, company, db_session):
    other_co = Company(company_id="CONFLICT", company_name="Conflict Co", status="active")
    db_session.add(other_co)
    db_session.commit()

    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, "CONFLICT", seeded_roles["company_admin"])

    token = _make_platform_admin_token(str(uuid4()))
    response = client.post(
        f"/v1/admin/companies/{company.company_id}/admins",
        json={"user_email": target.email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["detail"] == "existing_admin"


def test_api_assign_admin_force_true_succeeds(client, seeded_roles, company, db_session):
    other_co = Company(company_id="FORCO", company_name="Force Co", status="active")
    db_session.add(other_co)
    db_session.commit()

    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, "FORCO", seeded_roles["company_admin"])

    token = _make_platform_admin_token(str(uuid4()))
    response = client.post(
        f"/v1/admin/companies/{company.company_id}/admins?force=true",
        json={"user_email": target.email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "assigned"


def test_api_revoke_admin_204(client, seeded_roles, company, db_session):
    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, company.company_id, seeded_roles["company_admin"])

    token = _make_platform_admin_token(str(uuid4()))
    response = client.delete(
        f"/v1/admin/companies/{company.company_id}/admins/{target.user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_api_list_admins(client, seeded_roles, company, db_session):
    target = _create_user(db_session, user_type="company_employee")
    _grant_role(db_session, target, company.company_id, seeded_roles["company_admin"])

    token = _make_platform_admin_token(str(uuid4()))
    response = client.get(
        f"/v1/admin/companies/{company.company_id}/admins",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert any(m["user_id"] == target.user_id for m in data)
