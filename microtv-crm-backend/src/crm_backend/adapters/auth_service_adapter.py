"""Adapter for the external auth.microtv.ar service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError

from crm_backend.core.config import Settings
from crm_backend.core.exceptions import AuthenticationContextError, InvalidCredentialsError, UnauthenticatedError, UpstreamAuthError


@dataclass(slots=True)
class ActiveMembershipContext:
    """Represent the active membership extracted from an auth JWT.

    Attributes:
        membership_id: External auth membership id.
        tenant_type: External tenant type.
        tenant_id: External tenant identifier.
        roles: External roles bound to the active membership.
    """

    membership_id: str
    tenant_type: str
    tenant_id: str
    roles: list[str]


@dataclass(slots=True)
class AuthenticatedAuthResult:
    """Represent a successful external auth login.

    Attributes:
        access_token: Signed access token issued by auth.
        refresh_token: Signed refresh token issued by auth.
        token_type: Token type returned by auth.
        expires_in: Access token duration in seconds.
        refresh_expires_in: Refresh token duration in seconds.
        auth_user_id: External auth subject.
        email: Email extracted from the JWT.
        display_name: Optional display name when provided by the JWT.
        active_membership: Active membership snapshot extracted from the JWT.
        claims: Full decoded claims payload.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int
    auth_user_id: str
    email: str | None
    display_name: str | None
    active_membership: ActiveMembershipContext
    claims: dict[str, Any]


@dataclass(slots=True)
class ContextSelectionRequiredResult:
    """Represent a multi-membership response from auth.

    Attributes:
        login_ticket: Temporary login ticket issued by auth.
        memberships: Available memberships returned by auth.
    """

    login_ticket: str
    memberships: list[dict[str, Any]]


@dataclass(slots=True)
class AccessPendingResult:
    """Represent a pending-access response from auth.

    Attributes:
        user_type: External auth user type awaiting approval.
    """

    user_type: str


@dataclass(slots=True)
class AuthManagedUser:
    user_id: str
    email: str
    display_name: str
    is_active: bool
    roles: list[str]


class AuthServiceAdapter:
    """Encapsulate the HTTP and JWT contract of auth.microtv.ar."""

    def __init__(self, settings: Settings) -> None:
        """Create the adapter.

        Args:
            settings: Application settings.
        """

        self._settings = settings

    def login(self, *, email: str, password: str) -> AuthenticatedAuthResult | ContextSelectionRequiredResult | AccessPendingResult:
        """Authenticate against auth.microtv.ar.

        Args:
            email: User email sent by the frontend.
            password: User password sent by the frontend.

        Returns:
            AuthenticatedAuthResult | ContextSelectionRequiredResult | AccessPendingResult:
                Parsed auth response.
        """

        try:
            with httpx.Client(base_url=self._settings.auth_base_url, timeout=self._settings.auth_timeout_seconds) as client:
                response = client.post(self._settings.auth_login_path, json={"email": email, "password": password})
        except httpx.HTTPError as exc:
            raise UpstreamAuthError() from exc

        if response.status_code == 401:
            raise InvalidCredentialsError()

        if response.status_code >= 500:
            raise UpstreamAuthError("El servicio auth respondió con un error interno.")

        if response.status_code >= 400:
            detail = self._extract_error_detail(response)
            raise AuthenticationContextError(detail)

        payload = response.json()
        if payload.get("requires_context_selection"):
            return ContextSelectionRequiredResult(
                login_ticket=str(payload["login_ticket"]),
                memberships=list(payload.get("memberships", [])),
            )
        if payload.get("access_pending"):
            return AccessPendingResult(user_type=str(payload.get("user_type", "unknown")))
        return self._build_authenticated_result(payload)

    def validate_access_token(self, access_token: str) -> AuthenticatedAuthResult:
        """Validate and decode an auth-issued access token.

        Args:
            access_token: Bearer token to validate.

        Returns:
            AuthenticatedAuthResult: Parsed token context.
        """

        try:
            claims = self._decode_access_token(access_token)
            active_membership = self._extract_active_membership(claims)
        except AuthenticationContextError as exc:
            raise UnauthenticatedError("El token Bearer es inválido o expiró.") from exc

        return AuthenticatedAuthResult(
            access_token=access_token,
            refresh_token="",
            token_type="bearer",
            expires_in=max(int(claims.get("exp", 0) - datetime.now(UTC).timestamp()), 0),
            refresh_expires_in=0,
            auth_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=claims.get("display_name"),
            active_membership=active_membership,
            claims=claims,
        )

    def _build_authenticated_result(self, payload: dict[str, Any]) -> AuthenticatedAuthResult:
        """Convert an auth token response into a structured result.

        Args:
            payload: Raw JSON payload returned by auth.

        Returns:
            AuthenticatedAuthResult: Parsed auth login result.
        """

        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        if not access_token or not refresh_token:
            raise AuthenticationContextError("La respuesta de auth no contiene tokens válidos.")
        claims = self._decode_access_token(str(access_token))
        active_membership = self._extract_active_membership(claims)
        return AuthenticatedAuthResult(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            token_type=str(payload.get("token_type", "bearer")),
            expires_in=int(payload.get("expires_in", 0)),
            refresh_expires_in=int(payload.get("refresh_expires_in", 0)),
            auth_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=claims.get("display_name"),
            active_membership=active_membership,
            claims=claims,
        )

    def _decode_access_token(self, access_token: str) -> dict[str, Any]:
        """Decode an auth-issued access token.

        Args:
            access_token: JWT string.

        Returns:
            dict[str, Any]: Decoded claims payload.
        """

        try:
            claims = jwt.decode(
                access_token,
                self._settings.auth_jwt_secret,
                algorithms=[self._settings.auth_jwt_algorithm],
                issuer=self._settings.auth_jwt_issuer,
                audience=self._settings.auth_jwt_audience,
            )
        except InvalidTokenError as exc:
            raise AuthenticationContextError("El JWT devuelto por auth no pudo validarse.") from exc

        if "sub" not in claims:
            raise AuthenticationContextError("El JWT de auth no contiene el claim 'sub'.")
        return claims

    def _extract_active_membership(self, claims: dict[str, Any]) -> ActiveMembershipContext:
        """Extract the active membership snapshot from auth claims.

        Args:
            claims: Decoded JWT claims.

        Returns:
            ActiveMembershipContext: Structured membership context.
        """

        raw_membership = claims.get("active_membership")
        if not isinstance(raw_membership, dict):
            raise AuthenticationContextError("El JWT de auth no contiene 'active_membership' válido.")

        roles = raw_membership.get("roles", [])
        if not isinstance(roles, list):
            raise AuthenticationContextError("El claim 'active_membership.roles' es inválido.")

        membership_id = raw_membership.get("membership_id")
        tenant_type = raw_membership.get("tenant_type")
        tenant_id = raw_membership.get("tenant_id")
        if not membership_id or not tenant_type or not tenant_id:
            raise AuthenticationContextError("El claim 'active_membership' está incompleto.")

        return ActiveMembershipContext(
            membership_id=str(membership_id),
            tenant_type=str(tenant_type),
            tenant_id=str(tenant_id),
            roles=[str(role) for role in roles],
        )

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract a stable error detail from an auth response.

        Args:
            response: HTTP response from auth.

        Returns:
            str: Extracted error message.
        """

        try:
            payload = response.json()
        except ValueError:
            return "El servicio auth devolvió una respuesta no parseable."
        detail = payload.get("detail")
        return str(detail) if detail else "El servicio auth rechazó la solicitud."

    def list_managed_users(self, access_token: str) -> list[AuthManagedUser]:
        payload = self._call_crm_admin("GET", "/v1/crm-admin/users", access_token=access_token)
        if not isinstance(payload, list):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al listar usuarios.")
        return [self._build_managed_user(item) for item in payload if isinstance(item, dict)]

    def get_managed_user(self, access_token: str, user_id: str) -> AuthManagedUser:
        for user in self.list_managed_users(access_token):
            if user.user_id == user_id:
                return user
        raise AuthenticationContextError("User not found.")

    def create_managed_user(
        self,
        *,
        access_token: str,
        email: str,
        display_name: str,
        password: str,
        is_active: bool,
        roles: list[str],
    ) -> AuthManagedUser:
        payload = self._call_crm_admin(
            "POST",
            "/v1/crm-admin/users",
            access_token=access_token,
            body={
                "email": email,
                "display_name": display_name,
                "password": password,
                "is_active": is_active,
                "roles": roles,
            },
        )
        if not isinstance(payload, dict):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al crear usuario.")
        return self._build_managed_user(payload)

    def update_managed_user(self, *, access_token: str, user_id: str, email: str, display_name: str) -> AuthManagedUser:
        payload = self._call_crm_admin(
            "PUT",
            f"/v1/crm-admin/users/{user_id}",
            access_token=access_token,
            body={"email": email, "display_name": display_name},
        )
        if not isinstance(payload, dict):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al actualizar usuario.")
        return self._build_managed_user(payload)

    def set_managed_user_status(self, *, access_token: str, user_id: str, is_active: bool) -> AuthManagedUser:
        payload = self._call_crm_admin(
            "PUT",
            f"/v1/crm-admin/users/{user_id}/status",
            access_token=access_token,
            body={"is_active": is_active},
        )
        if not isinstance(payload, dict):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al cambiar estado de usuario.")
        return self._build_managed_user(payload)

    def set_managed_user_roles(self, *, access_token: str, user_id: str, roles: list[str]) -> AuthManagedUser:
        payload = self._call_crm_admin(
            "PUT",
            f"/v1/crm-admin/users/{user_id}/roles",
            access_token=access_token,
            body={"roles": roles},
        )
        if not isinstance(payload, dict):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al asignar roles.")
        return self._build_managed_user(payload)

    def reset_managed_user_password(self, *, access_token: str, user_id: str, new_password: str) -> AuthManagedUser:
        payload = self._call_crm_admin(
            "PUT",
            f"/v1/crm-admin/users/{user_id}/reset-password",
            access_token=access_token,
            body={"new_password": new_password},
        )
        if not isinstance(payload, dict):
            raise UpstreamAuthError("El servicio auth devolvió una respuesta inválida al resetear contraseña.")
        return self._build_managed_user(payload)

    def _call_crm_admin(self, method: str, path: str, *, access_token: str, body: dict[str, Any] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(base_url=self._settings.auth_base_url, timeout=self._settings.auth_timeout_seconds) as client:
                response = client.request(method, path, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamAuthError() from exc

        if response.status_code == 403:
            detail = self._extract_error_detail(response).lower()
            if "admin role required" in detail or "admin or ejecutivo role required" in detail:
                management_access_token = self._login_management_user_access_token()
                if management_access_token:
                    retry_headers = {"Authorization": f"Bearer {management_access_token}"}
                    try:
                        with httpx.Client(base_url=self._settings.auth_base_url, timeout=self._settings.auth_timeout_seconds) as client:
                            response = client.request(method, path, json=body, headers=retry_headers)
                    except httpx.HTTPError as exc:
                        raise UpstreamAuthError() from exc

        if response.status_code >= 500:
            raise UpstreamAuthError("El servicio auth respondió con un error interno.")
        if response.status_code >= 400:
            detail = self._extract_error_detail(response)
            if response.status_code == 401:
                raise UnauthenticatedError(detail)
            raise AuthenticationContextError(detail)

        return response.json()

    def _login_management_user_access_token(self) -> str | None:
        management_email = self._settings.auth_management_email.strip()
        management_password = self._settings.auth_management_password.strip()
        if not management_email or not management_password:
            return None

        try:
            with httpx.Client(base_url=self._settings.auth_base_url, timeout=self._settings.auth_timeout_seconds) as client:
                response = client.post(
                    self._settings.auth_login_path,
                    json={"email": management_email, "password": management_password},
                )
        except httpx.HTTPError as exc:
            raise UpstreamAuthError() from exc

        if response.status_code >= 500:
            raise UpstreamAuthError("El servicio auth respondió con un error interno.")
        if response.status_code >= 400:
            return None

        payload = response.json()
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            return None
        return access_token

    def _build_managed_user(self, payload: dict[str, Any]) -> AuthManagedUser:
        return AuthManagedUser(
            user_id=str(payload.get("user_id", "")),
            email=str(payload.get("email", "")),
            display_name=str(payload.get("display_name", "")),
            is_active=bool(payload.get("is_active", False)),
            roles=[str(role) for role in payload.get("roles", []) if isinstance(role, str)],
        )

    def request_password_reset(self, *, email: str, recaptcha_token: str) -> None:
        """Trigger auth forgot-password flow for the provided email."""

        body = {
            "email": email,
            "recaptcha_token": recaptcha_token,
        }
        try:
            with httpx.Client(base_url=self._settings.auth_base_url, timeout=self._settings.auth_timeout_seconds) as client:
                response = client.post("/v1/auth/forgot-password", json=body)
        except httpx.HTTPError as exc:
            raise UpstreamAuthError() from exc

        if response.status_code >= 500:
            raise UpstreamAuthError("El servicio auth respondió con un error interno.")
        if response.status_code >= 400:
            detail = self._extract_error_detail(response)
            raise AuthenticationContextError(detail)
