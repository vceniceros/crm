from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models import Membership, Role, RoleAssignment, User
from src.security.passwords import hash_password
from src.services.crm_identity_service import CrmIdentityService


def _create_user(db_session: Session, *, email: str | None = None, display_name: str = "Test User") -> User:
    user = User(
        display_name=display_name,
        email=email or f"user-{uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        status="active",
        email_verified=True,
        user_type="company_employee",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _set_crm_roles(db_session: Session, *, user_id: str, role_names: list[str]) -> None:
    membership = db_session.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.tenant_type == settings.crm_auth_tenant_type,
            Membership.tenant_id == settings.crm_auth_tenant_id,
        )
    )
    if membership is None:
        membership = Membership(
            user_id=user_id,
            tenant_type=settings.crm_auth_tenant_type,
            tenant_id=settings.crm_auth_tenant_id,
        )
        db_session.add(membership)
        db_session.flush()

    existing_assignments = db_session.scalars(
        select(RoleAssignment).where(RoleAssignment.membership_id == membership.membership_id)
    ).all()
    for assignment in existing_assignments:
        db_session.delete(assignment)

    if role_names:
        role_rows = db_session.scalars(select(Role).where(Role.role_name.in_(role_names))).all()
        role_map = {role.role_name: role for role in role_rows}
        for role_name in sorted(set(role_names)):
            role = role_map.get(role_name)
            if role is None:
                raise RuntimeError(f"Missing role seed for '{role_name}'")
            db_session.add(RoleAssignment(membership_id=membership.membership_id, role_id=role.role_id))

    db_session.commit()


def _make_crm_token(user_id: str, roles: list[str]) -> str:
    from src.security.jwt import create_access_token

    mock_user = type("_U", (), {"user_id": user_id, "email": "actor@test.com"})()
    membership = {
        "membership_id": str(uuid4()),
        "tenant_type": settings.crm_auth_tenant_type,
        "tenant_id": settings.crm_auth_tenant_id,
        "roles": roles,
    }
    return create_access_token(mock_user, membership)


def _make_headers(user_id: str, roles: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_crm_token(user_id, roles)}"}


def test_executive_can_create_non_admin_user(client, db_session: Session):
    CrmIdentityService(db_session).ensure_operational_roles()
    db_session.commit()

    actor = _create_user(db_session)
    headers = _make_headers(actor.user_id, ["ejecutivo"])

    response = client.post(
        "/v1/crm-admin/users",
        json={
            "email": "nuevo.ejecutivo@test.com",
            "display_name": "Nuevo Ejecutivo",
            "password": "password123",
            "is_active": True,
            "roles": ["operador_deposito"],
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "nuevo.ejecutivo@test.com"
    assert data["roles"] == ["operador_deposito"]


def test_executive_cannot_create_admin_user(client, db_session: Session):
    CrmIdentityService(db_session).ensure_operational_roles()
    db_session.commit()

    actor = _create_user(db_session)
    headers = _make_headers(actor.user_id, ["ejecutivo"])

    response = client.post(
        "/v1/crm-admin/users",
        json={
            "email": "nuevo.admin@test.com",
            "display_name": "Nuevo Admin",
            "password": "password123",
            "is_active": True,
            "roles": ["admin"],
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "ejecutivo cannot assign admin role."


def test_executive_cannot_edit_admin_user(client, db_session: Session):
    identity_service = CrmIdentityService(db_session)
    identity_service.ensure_operational_roles()
    db_session.commit()

    actor = _create_user(db_session, email="actor@test.com")
    admin_target = _create_user(db_session, email="target.admin@test.com")
    _set_crm_roles(db_session, user_id=admin_target.user_id, role_names=["admin"])

    headers = _make_headers(actor.user_id, ["ejecutivo"])
    response = client.put(
        f"/v1/crm-admin/users/{admin_target.user_id}",
        json={"email": "target.admin.updated@test.com", "display_name": "Admin Editado"},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "ejecutivo cannot manage admin users."


def test_executive_can_edit_non_admin_user(client, db_session: Session):
    identity_service = CrmIdentityService(db_session)
    identity_service.ensure_operational_roles()
    db_session.commit()

    actor = _create_user(db_session, email="actor2@test.com")
    target = _create_user(db_session, email="target.nonadmin@test.com")
    _set_crm_roles(db_session, user_id=target.user_id, role_names=["operador_deposito"])

    headers = _make_headers(actor.user_id, ["ejecutivo"])
    response = client.put(
        f"/v1/crm-admin/users/{target.user_id}",
        json={"email": "target.nonadmin.updated@test.com", "display_name": "Operador Editado"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "target.nonadmin.updated@test.com"
    assert data["display_name"] == "Operador Editado"


def test_executive_can_reset_non_admin_password_but_not_admin(client, db_session: Session):
    identity_service = CrmIdentityService(db_session)
    identity_service.ensure_operational_roles()
    db_session.commit()

    actor = _create_user(db_session, email="actor3@test.com")
    non_admin_target = _create_user(db_session, email="target.reset@test.com")
    admin_target = _create_user(db_session, email="target.reset.admin@test.com")
    _set_crm_roles(db_session, user_id=non_admin_target.user_id, role_names=["operador_deposito"])
    _set_crm_roles(db_session, user_id=admin_target.user_id, role_names=["admin"])

    headers = _make_headers(actor.user_id, ["ejecutivo"])

    ok_response = client.put(
        f"/v1/crm-admin/users/{non_admin_target.user_id}/reset-password",
        json={"new_password": "newpassword123"},
        headers=headers,
    )
    blocked_response = client.put(
        f"/v1/crm-admin/users/{admin_target.user_id}/reset-password",
        json={"new_password": "newpassword123"},
        headers=headers,
    )

    assert ok_response.status_code == 200
    assert blocked_response.status_code == 403
    assert blocked_response.json()["detail"] == "ejecutivo cannot manage admin users."
