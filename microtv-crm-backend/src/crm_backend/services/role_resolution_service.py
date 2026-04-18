"""Políticas de resolución de roles del CRM."""

from crm_backend.adapters.auth_service_adapter import AuthenticatedAuthResult
from crm_backend.core.config import Settings
from crm_backend.core.exceptions import CrmAuthorizationError
from crm_backend.models import CrmUser
from crm_backend.repositories import CrmRoleRepository, CrmUserRepository


class RoleResolutionService:
    """Resuelve o bootstrappea roles locales del CRM desde el contexto autenticado."""

    ROLE_KEY_ALIASES = {
        "admin_crm": "admin",
        "encargado_deposito": "deposito",
        "tecnico_campo": "tecnico",
    }

    def __init__(self, settings: Settings, role_repository: CrmRoleRepository, user_repository: CrmUserRepository) -> None:
        """Crea el servicio.

        Args:
            settings: Configuración de la aplicación.
            role_repository: Repositorio de roles locales del CRM.
            user_repository: Repositorio de usuarios locales del CRM.
        """

        self._settings = settings
        self._role_repository = role_repository
        self._user_repository = user_repository

    def ensure_local_roles(self, crm_user: CrmUser, auth_result: AuthenticatedAuthResult) -> list[str]:
        """Garantiza que el usuario tenga al menos un rol local del CRM.

        Args:
            crm_user: Usuario local del CRM.
            auth_result: Resultado parseado del login externo.

        Returns:
            list[str]: Claves ordenadas de roles locales del CRM.
        """

        bootstrap_role_key = self._map_auth_roles_to_crm_role(auth_result)
        local_roles = self._collect_local_role_keys(crm_user)

        if bootstrap_role_key is not None and self._settings.auto_provision_crm_role:
            crm_role = self._role_repository.get_by_key(bootstrap_role_key)
            if crm_role is None:
                raise CrmAuthorizationError("El rol local requerido no existe en la base del CRM.")
            self._user_repository.assign_role_if_missing(crm_user, crm_role)
            local_roles = self._collect_local_role_keys(crm_user)

        if local_roles:
            return local_roles

        if not self._settings.auto_provision_crm_role:
            raise CrmAuthorizationError()

        raise CrmAuthorizationError(
            "El usuario autenticado no tiene un mapeo de bootstrap hacia un rol local del CRM."
        )

    def select_primary_role(self, role_keys: list[str]) -> str:
        """Selecciona la clave de rol que debe conducir el frontend actual.

        Args:
            role_keys: Claves de rol locales disponibles.

        Returns:
            str: Clave del rol principal.
        """

        priority = ["admin", "ejecutivo", "tecnico", "deposito"]
        for role_key in priority:
            if role_key in role_keys:
                return role_key
        raise CrmAuthorizationError()

    def _collect_local_role_keys(self, crm_user: CrmUser) -> list[str]:
        """Recolecta claves ordenadas de roles locales desde un usuario CRM.

        Args:
            crm_user: Usuario local del CRM.

        Returns:
            list[str]: Claves de rol locales ordenadas.
        """

        return sorted(
            {
                self.ROLE_KEY_ALIASES.get(assignment.role.role_key, assignment.role.role_key)
                for assignment in crm_user.assigned_roles
                if assignment.role and assignment.role.is_active
            }
        )

    def _map_auth_roles_to_crm_role(self, auth_result: AuthenticatedAuthResult) -> str | None:
        """Mapea roles externos de auth a un rol bootstrap del CRM.

        Args:
            auth_result: Resultado autenticado de auth con membresía activa.

        Returns:
            str | None: Clave del rol bootstrap del CRM cuando exista mapeo.
        """

        auth_role_set = {role for role in auth_result.active_membership.roles}
        if auth_role_set.intersection(self._settings.default_admin_auth_roles):
            return "admin_crm"
        if "ejecutivo" in auth_role_set:
            return "ejecutivo"
        if (
            auth_result.active_membership.tenant_type == "company"
            and auth_result.active_membership.tenant_id == self._settings.deposito_demo_tenant_id
            and auth_role_set.intersection(self._settings.default_deposito_auth_roles)
        ):
            return "encargado_deposito"
        if auth_role_set.intersection(self._settings.default_tech_auth_roles):
            return "tecnico_campo"
        return None
