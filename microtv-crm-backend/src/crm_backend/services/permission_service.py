"""Permission resolution and updates."""

from __future__ import annotations

from crm_backend.core.exceptions import ApplicationError
from crm_backend.models import CrmUser, UserPermission
from crm_backend.repositories import CrmUserRepository, PermissionRepository
from crm_backend.services.auth_service import ResolvedCrmSession


PERMISSION_STOCK_MANAGE = "stock.manage"
PERMISSION_STOCK_DELETE_PRODUCT = "stock.delete_product"
PERMISSION_TICKET_REASSIGN = "ticket.reassign"
PERMISSION_ORDER_REASSIGN = "order.reassign"
PERMISSION_COMMENT_DELETE = "comment.delete"

KNOWN_PERMISSION_CODES = [
    PERMISSION_STOCK_MANAGE,
    PERMISSION_STOCK_DELETE_PRODUCT,
    PERMISSION_TICKET_REASSIGN,
    PERMISSION_ORDER_REASSIGN,
    PERMISSION_COMMENT_DELETE,
]


class PermissionService:
    """Resolve effective permissions from role defaults and user overrides."""

    ROLE_KEY_ALIASES = {
        "admin_crm": "admin",
        "encargado_deposito": "deposito",
        "tecnico_campo": "tecnico",
    }

    def __init__(self, repository: PermissionRepository, user_repository: CrmUserRepository) -> None:
        self._repository = repository
        self._user_repository = user_repository

    def resolve(self, actor_role_keys: list[str], crm_user_id: str, code: str) -> bool:
        normalized_roles = [self._normalize_role_key(role_key) for role_key in actor_role_keys]
        normalized_roles = [role_key for role_key in normalized_roles if role_key]
        if "admin" in normalized_roles:
            return True

        user_override = self._find_user_override(crm_user_id, code)
        if user_override is not None:
            return user_override.is_granted

        matched_role_permissions = []
        for role_key in normalized_roles:
            matched_role_permissions.extend(self._repository.get_role_permissions(role_key))

        for permission in matched_role_permissions:
            if permission.permission_code == code and permission.is_granted:
                return True
        for permission in matched_role_permissions:
            if permission.permission_code == code:
                return False
        return False

    def get_effective_permissions(self, role_keys: list[str], crm_user_id: str) -> dict[str, bool]:
        return {code: self.resolve(role_keys, crm_user_id, code) for code in KNOWN_PERMISSION_CODES}

    def update_role_permission(self, actor: ResolvedCrmSession, role_key: str, code: str, is_granted: bool):
        self._ensure_admin(actor)
        normalized_role = self._normalize_role_key(role_key)
        self._ensure_known_permission_code(code)
        if not normalized_role:
            raise ApplicationError("permission_role_required", "Debe indicar un rol válido.", 422)
        return self._repository.set_role_permission(
            normalized_role,
            code,
            is_granted,
            actor_id=actor.crm_user.crm_user_id,
        )

    def update_user_permission(
        self,
        actor: ResolvedCrmSession,
        target_user_id: str,
        code: str,
        is_granted: bool,
    ) -> UserPermission:
        self._ensure_admin_or_executive(actor)
        self._ensure_known_permission_code(code)
        target_user = self._get_target_user(target_user_id)
        if "ejecutivo" in actor.role_keys and self._user_has_admin_role(target_user):
            raise ApplicationError(
                "permission_forbidden_on_admin",
                "Un ejecutivo no puede modificar permisos de un administrador.",
                403,
            )
        if "admin" not in actor.role_keys:
            raise ApplicationError("permission_admin_required", "La operación requiere rol administrador.", 403)

        return self._repository.set_user_permission(
            target_user_id,
            code,
            is_granted,
            granted_by=actor.crm_user.crm_user_id,
        )

    def delete_user_permission(self, actor: ResolvedCrmSession, target_user_id: str, code: str) -> None:
        self._ensure_admin(actor)
        self._ensure_known_permission_code(code)
        self._get_target_user(target_user_id)
        self._repository.delete_user_permission(target_user_id, code)

    def list_role_permissions(self):
        return self._repository.get_all_role_permissions()

    def list_user_overrides(self):
        return self._repository.list_user_overrides()

    def get_user_overrides(self, crm_user_id: str):
        return self._repository.get_user_overrides(crm_user_id)

    def _find_user_override(self, crm_user_id: str, code: str) -> UserPermission | None:
        for override in self._repository.get_user_overrides(crm_user_id):
            if override.permission_code == code:
                return override
        return None

    def _ensure_known_permission_code(self, code: str) -> None:
        if code not in KNOWN_PERMISSION_CODES:
            raise ApplicationError("permission_code_invalid", "El código de permiso indicado no existe.", 422)

    def _ensure_admin(self, actor: ResolvedCrmSession) -> None:
        if "admin" not in actor.role_keys:
            raise ApplicationError("permission_admin_required", "La operación requiere rol administrador.", 403)

    def _ensure_admin_or_executive(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "ejecutivo" in actor.role_keys:
            return
        raise ApplicationError("permission_access_denied", "No tiene permisos para esta operación.", 403)

    def _get_target_user(self, target_user_id: str) -> CrmUser:
        user = self._user_repository.get_by_id(target_user_id)
        if user is None or user.deleted_at is not None:
            raise ApplicationError("permission_user_not_found", "El usuario indicado no existe.", 404)
        return user

    def _user_has_admin_role(self, user: CrmUser) -> bool:
        for assignment in user.assigned_roles:
            role = assignment.role
            normalized = self._normalize_role_key(getattr(role, "role_key", None))
            if normalized == "admin":
                return True
        return False

    def _normalize_role_key(self, role_key: str | None) -> str | None:
        if not isinstance(role_key, str):
            return None
        normalized = role_key.strip()
        return self.ROLE_KEY_ALIASES.get(normalized, normalized) or None
