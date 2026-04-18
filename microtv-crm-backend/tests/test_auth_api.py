"""Authentication API tests."""

from __future__ import annotations

from sqlalchemy import select

from crm_backend.adapters.auth_service_adapter import (
    AccessPendingResult,
    ActiveMembershipContext,
    AuthenticatedAuthResult,
    ContextSelectionRequiredResult,
)
from crm_backend.api.dependencies import get_auth_service_adapter
from crm_backend.core.exceptions import InvalidCredentialsError
from crm_backend.models import CrmRole, CrmUser, CrmUserRole


class FakeAuthAdapter:
    """Fake auth adapter for endpoint tests."""

    def __init__(
        self,
        mode: str = "authenticated",
        roles: list[str] | None = None,
        tenant_id: str = "MICROTV",
        auth_user_id: str = "auth-user-1",
        email: str = "admin.crm@microtv.com",
        display_name: str = "Admin MicroTV",
    ) -> None:
        """Create the fake adapter.

        Args:
            mode: Response mode emitted by the fake adapter.
            roles: Active auth roles returned for authenticated flows.
            tenant_id: Tenant id returned for the active membership.
        """

        self._mode = mode
        self._roles = roles or ["platform_admin"]
        self._tenant_id = tenant_id
        self._auth_user_id = auth_user_id
        self._email = email
        self._display_name = display_name

    def login(self, *, email: str, password: str):
        """Return a deterministic login result.

        Args:
            email: User email.
            password: User password.

        Returns:
            object: Fake adapter result.
        """

        if self._mode == "invalid":
            raise InvalidCredentialsError()
        if self._mode == "context":
            return ContextSelectionRequiredResult(
                login_ticket="ticket-123",
                memberships=[
                    {
                        "membership_id": "membership-a",
                        "tenant_type": "company",
                        "tenant_id": self._tenant_id,
                        "roles": self._roles,
                    }
                ],
            )
        if self._mode == "pending":
            return AccessPendingResult(user_type="company_employee")
        return self.validate_access_token("access-token")

    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
        """Return a deterministic authenticated token payload.

        Args:
            access_token: Ignored test token.

        Returns:
            AuthenticatedAuthResult: Fake authenticated result.
        """

        return AuthenticatedAuthResult(
            access_token=access_token,
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=3600,
            refresh_expires_in=86400,
            auth_user_id=self._auth_user_id,
            email=self._email,
            display_name=self._display_name,
            active_membership=ActiveMembershipContext(
                membership_id="membership-a",
                tenant_type="company",
                tenant_id=self._tenant_id,
                roles=self._roles,
            ),
            claims={
                "sub": self._auth_user_id,
                "email": self._email,
                "active_membership": {
                    "membership_id": "membership-a",
                    "tenant_type": "company",
                    "tenant_id": self._tenant_id,
                    "roles": self._roles,
                },
            },
        )


def test_login_returns_authenticated_session(client) -> None:
    """`POST /auth/login` should return a usable CRM session."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(mode="authenticated")

    response = client.post(
        "/auth/login",
        json={"email": "admin.crm@microtv.com", "password": "Passw0rd!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["user"]["auth_user_id"] == "auth-user-1"
    assert body["user"]["primary_role"] == "admin"
    assert body["user"]["role_keys"] == ["admin"]


def test_login_bootstraps_ejecutivo_role(client) -> None:
    """`POST /auth/login` should bootstrap the ejecutivo role from auth."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(
        mode="authenticated",
        roles=["ejecutivo"],
    )

    response = client.post(
        "/auth/login",
        json={"email": "ejecutivo.crm@yccbrothers.com", "password": "Passw0rd!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["user"]["primary_role"] == "ejecutivo"
    assert body["user"]["role_keys"] == ["ejecutivo"]


def test_login_prioritizes_tecnico_over_deposito_when_both_roles_exist(client, db_session) -> None:
    """`POST /auth/login` should resolve the technical UI role when both local roles are present."""

    tecnico_role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == "tecnico_campo"))
    if tecnico_role is None:
        raise AssertionError("No se encontró el rol tecnico_campo seed.")

    tecnico_user = CrmUser(
        auth_user_id="auth-user-1",
        email="tecnico.campo@yccbrothers.com",
        display_name="Tecnico Campo",
    )
    tecnico_user.assigned_roles.append(
        CrmUserRole(
            crm_role_id=tecnico_role.crm_role_id,
            role=tecnico_role,
        )
    )
    db_session.add(tecnico_user)
    db_session.commit()

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(
        mode="authenticated",
        roles=["company_operator"],
        tenant_id="YCC",
    )

    response = client.post(
        "/auth/login",
        json={"email": "tecnico.campo@yccbrothers.com", "password": "Passw0rd!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["user"]["primary_role"] == "tecnico"
    assert body["user"]["role_keys"] == ["deposito", "tecnico"]


def test_login_reuses_existing_operational_user_when_auth_subject_changed(client, db_session) -> None:
    """`POST /auth/login` should reconcile duplicate CRM users by email and keep the operational assignee record."""

    deposito_role = db_session.scalar(select(CrmRole).where(CrmRole.role_key == "encargado_deposito"))
    if deposito_role is None:
        raise AssertionError("No se encontró el rol encargado_deposito seed.")

    canonical_user = CrmUser(
        auth_user_id="legacy-auth-user",
        email="operador.crm@yccbrothers.com",
        display_name="Operador Deposito YCC",
    )
    canonical_user.assigned_roles.append(
        CrmUserRole(
            crm_role_id=deposito_role.crm_role_id,
            role=deposito_role,
        )
    )
    db_session.add(canonical_user)
    db_session.flush()

    duplicate_user = CrmUser(
        auth_user_id="auth-user-1",
        email="operador.crm@yccbrothers.com",
        display_name="Operador Crm",
    )
    db_session.add(duplicate_user)
    db_session.commit()

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(
        mode="authenticated",
        roles=["company_operator"],
        tenant_id="YCC",
        auth_user_id="auth-user-1",
        email="operador.crm@yccbrothers.com",
        display_name="Operador Crm",
    )

    response = client.post(
        "/auth/login",
        json={"email": "operador.crm@yccbrothers.com", "password": "Passw0rd!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["user"]["crm_user_id"] == canonical_user.crm_user_id
    assert body["user"]["primary_role"] == "deposito"
    assert body["user"]["role_keys"] == ["deposito"]

    db_session.refresh(canonical_user)
    db_session.refresh(duplicate_user)
    assert canonical_user.auth_user_id == "auth-user-1"
    assert duplicate_user.deleted_at is not None
    assert duplicate_user.is_active_in_crm is False


def test_login_returns_context_selection_when_auth_requires_it(client) -> None:
    """`POST /auth/login` should proxy context selection requirements."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(mode="context")

    response = client.post(
        "/auth/login",
        json={"email": "admin.crm@microtv.com", "password": "Passw0rd!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "context_selection_required"
    assert body["login_ticket"] == "ticket-123"


def test_get_me_returns_authenticated_session(client) -> None:
    """`GET /auth/me` should resolve the bearer token into a CRM session."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(mode="authenticated")

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authenticated"
    assert body["tokens"]["access_token"] == "access-token"


def test_get_me_rejects_invalid_bearer_token_with_401(client) -> None:
    """`GET /auth/me` should treat malformed stored tokens as unauthenticated."""

    client.app.dependency_overrides.pop(get_auth_service_adapter, None)

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthenticated"


def test_login_rejects_invalid_credentials(client) -> None:
    """`POST /auth/login` should expose invalid credentials with a stable error envelope."""

    client.app.dependency_overrides[get_auth_service_adapter] = lambda: FakeAuthAdapter(mode="invalid")

    response = client.post(
        "/auth/login",
        json={"email": "admin.crm@microtv.com", "password": "wrong"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"
