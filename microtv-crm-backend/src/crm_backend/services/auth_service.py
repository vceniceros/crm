"""Servicio de aplicación de autenticación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from crm_backend.adapters.auth_service_adapter import (
    AccessPendingResult,
    ActiveMembershipContext,
    AuthServiceAdapter,
    AuthenticatedAuthResult,
    ContextSelectionRequiredResult,
)
from crm_backend.models import CrmUser
from crm_backend.repositories import CrmUserRepository
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.role_resolution_service import RoleResolutionService


@dataclass(slots=True)
class ResolvedCrmSession:
    """Representa una sesión autenticada del CRM lista para el frontend.

    Attributes:
        crm_user: Usuario CRM persistido.
        primary_role: Rol principal del CRM para el frontend.
        role_keys: Todas las claves de rol activas del CRM.
        auth_result: Resultado parseado de auth externo.
    """

    crm_user: CrmUser
    primary_role: str
    role_keys: list[str]
    auth_result: AuthenticatedAuthResult


class AuthApplicationService:
    """Orquesta el login del CRM y la resolución del contexto autenticado."""

    def __init__(
        self,
        auth_adapter: AuthServiceAdapter,
        user_repository: CrmUserRepository,
        role_resolution_service: RoleResolutionService,
        activity_log_service: ActivityLogService,
    ) -> None:
        """Crea el servicio.

        Args:
            auth_adapter: Adapter hacia auth.microtv.ar.
            user_repository: Repositorio de usuarios CRM.
            role_resolution_service: Servicio que resuelve roles locales del CRM.
        """

        self._auth_adapter = auth_adapter
        self._user_repository = user_repository
        self._role_resolution_service = role_resolution_service
        self._activity_log_service = activity_log_service

    def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> ResolvedCrmSession | ContextSelectionRequiredResult | AccessPendingResult:
        """Autentica un usuario contra auth y aprovisiona el perfil local del CRM.

        Args:
            email: Email del usuario.
            password: Contraseña del usuario.

        Returns:
            ResolvedCrmSession | ContextSelectionRequiredResult | AccessPendingResult:
                Resultado estructurado del login del CRM.
        """

        auth_result = self._auth_adapter.login(email=email, password=password)
        if isinstance(auth_result, (ContextSelectionRequiredResult, AccessPendingResult)):
            return auth_result
        return self._resolve_crm_session(auth_result, log_login=True, ip_address=ip_address)

    def resolve_session_from_token(self, access_token: str) -> ResolvedCrmSession:
        """Resuelve un token existente de auth hacia una sesión del CRM.

        Args:
            access_token: Bearer token emitido por auth.

        Returns:
            ResolvedCrmSession: Sesión estructurada del CRM.
        """

        auth_result = self._auth_adapter.validate_access_token(access_token)
        return self._resolve_crm_session(auth_result, log_login=False, ip_address=None)

    def _resolve_crm_session(
        self,
        auth_result: AuthenticatedAuthResult,
        *,
        log_login: bool,
        ip_address: str | None,
    ) -> ResolvedCrmSession:
        """Aprovisiona estado local y resuelve roles locales del CRM.

        Args:
            auth_result: Resultado parseado de auth externo.

        Returns:
            ResolvedCrmSession: Sesión resuelta del CRM.
        """

        crm_user = self._user_repository.get_by_auth_user_id(auth_result.auth_user_id)
        email_candidates = self._user_repository.list_by_email(auth_result.email) if auth_result.email else []
        email_matched_user = self._select_preferred_user(auth_result.auth_user_id, crm_user, email_candidates)

        if crm_user is not None and email_matched_user is not None and crm_user.crm_user_id != email_matched_user.crm_user_id:
            crm_user = self._user_repository.reconcile_duplicate_identity(email_matched_user, crm_user, auth_result.auth_user_id)
        elif crm_user is None and email_matched_user is not None:
            email_matched_user.auth_user_id = auth_result.auth_user_id
            crm_user = email_matched_user
        elif crm_user is None:
            crm_user = self._user_repository.create(auth_result.auth_user_id)

        now = datetime.now(UTC)
        crm_user.sync_identity_snapshot(
            email=auth_result.email,
            display_name=auth_result.display_name or self._derive_display_name(auth_result.email),
            synced_at=now,
        )
        crm_user.sync_auth_context(
            membership_id=auth_result.active_membership.membership_id,
            tenant_type=auth_result.active_membership.tenant_type,
            tenant_id=auth_result.active_membership.tenant_id,
            roles=auth_result.active_membership.roles,
            synced_at=now,
        )
        crm_user.register_successful_login(now)

        role_keys = self._role_resolution_service.ensure_local_roles(crm_user, auth_result)
        primary_role = self._role_resolution_service.select_primary_role(role_keys)
        persisted_user = self._user_repository.save(crm_user)
        resolved = ResolvedCrmSession(
            crm_user=persisted_user,
            primary_role=primary_role,
            role_keys=role_keys,
            auth_result=auth_result,
        )
        if log_login:
            self._activity_log_service.log(
                "auth.login",
                resolved,
                entity_type="crm_user",
                entity_id=resolved.crm_user.crm_user_id,
                entity_label=resolved.crm_user.display_name or resolved.crm_user.email,
                summary="Login exitoso en CRM.",
                extra={"primary_role": primary_role},
                ip_address=ip_address,
            )
        return resolved

    def _select_preferred_user(
        self,
        auth_user_id: str,
        auth_matched_user: CrmUser | None,
        email_candidates: list[CrmUser],
    ) -> CrmUser | None:
        """Prefer the operational CRM user when the same email exists more than once."""

        if not email_candidates:
            return auth_matched_user

        if len(email_candidates) == 1:
            return email_candidates[0]

        def sort_key(user: CrmUser) -> tuple[int, int, int, str]:
            operational_refs = self._user_repository.count_operational_references(user.crm_user_id)
            role_count = len(user.assigned_roles)
            auth_match = 1 if user.auth_user_id == auth_user_id else 0
            # Higher operational usage wins; ties prefer more roles, then current auth match.
            return (-operational_refs, -role_count, -auth_match, user.crm_user_id)

        return sorted(email_candidates, key=sort_key)[0]

    def _derive_display_name(self, email: str | None) -> str | None:
        """Deriva un nombre visible de respaldo cuando auth no lo provee.

        Args:
            email: Claim de email proveniente del JWT de auth.

        Returns:
            str | None: Nombre visible de respaldo.
        """

        if not email or "@" not in email:
            return None
        local_part = email.split("@", maxsplit=1)[0]
        normalized = local_part.replace(".", " ").replace("_", " ").strip()
        return normalized.title() if normalized else email
