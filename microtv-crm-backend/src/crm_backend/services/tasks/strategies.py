"""Strategies for task items and next-assignment rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from crm_backend.core.exceptions import TaskValidationError
from crm_backend.models import CrmUser
from crm_backend.models.task_execution import Subtask, SubtaskItemValue, SubtaskStatus
from crm_backend.models.task_template import NextAssignmentPolicy, TemplateItemType
from crm_backend.repositories import CrmUserRepository


def _user_has_role(user: CrmUser, role_key: str) -> bool:
    return any(
        assignment.role is not None and assignment.role.role_key in {role_key, _reverse_alias(role_key)}
        for assignment in user.assigned_roles
    )


def _reverse_alias(role_key: str) -> str:
    aliases = {
        "admin": "admin_crm",
        "deposito": "encargado_deposito",
        "tecnico": "tecnico_campo",
    }
    return aliases.get(role_key, role_key)


class SubtaskItemValueStrategy:
    """Base strategy for instanced subtask item values."""

    def apply(self, item: SubtaskItemValue, payload: dict[str, object], actor_crm_user_id: str) -> None:
        raise NotImplementedError

    def is_completed(self, item: SubtaskItemValue) -> bool:
        raise NotImplementedError


class CheckboxItemValueStrategy(SubtaskItemValueStrategy):
    def apply(self, item: SubtaskItemValue, payload: dict[str, object], actor_crm_user_id: str) -> None:
        if "checkbox_value" not in payload:
            return

        checkbox_value = bool(payload.get("checkbox_value"))
        item.checkbox_value = checkbox_value
        item.completed_at = datetime.now(UTC) if checkbox_value else None
        item.last_updated_by_crm_user_id = actor_crm_user_id

    def is_completed(self, item: SubtaskItemValue) -> bool:
        return bool(item.checkbox_value)


class TextItemValueStrategy(SubtaskItemValueStrategy):
    def apply(self, item: SubtaskItemValue, payload: dict[str, object], actor_crm_user_id: str) -> None:
        if "text_value" not in payload:
            return

        # Saving progress must allow empty text values; strict completion is validated on close action.
        raw_value = payload.get("text_value")
        text_value = str(raw_value).strip() if raw_value is not None else ""
        item.text_value = text_value or None
        item.completed_at = datetime.now(UTC) if text_value else None
        item.last_updated_by_crm_user_id = actor_crm_user_id

    def is_completed(self, item: SubtaskItemValue) -> bool:
        return bool((item.text_value or "").strip())


class SubtaskItemValueStrategyRegistry:
    """Resolve item strategies by type."""

    def __init__(self) -> None:
        self._strategies = {
            TemplateItemType.CHECKBOX.value: CheckboxItemValueStrategy(),
            TemplateItemType.TEXT.value: TextItemValueStrategy(),
        }

    def get(self, item_type: str) -> SubtaskItemValueStrategy:
        strategy = self._strategies.get(item_type)
        if strategy is None:
            raise TaskValidationError(f"Tipo de item no soportado: '{item_type}'.")
        return strategy


@dataclass(slots=True)
class AssignmentResolution:
    assignee_crm_user_id: str | None
    next_status: str


class NextAssignmentStrategy:
    def resolve(
        self,
        subtask: Subtask,
        next_assigned_crm_user_id: str | None,
        user_repository: CrmUserRepository,
    ) -> AssignmentResolution:
        raise NotImplementedError


class RoleQueueAssignmentStrategy(NextAssignmentStrategy):
    def resolve(
        self,
        subtask: Subtask,
        next_assigned_crm_user_id: str | None,
        user_repository: CrmUserRepository,
    ) -> AssignmentResolution:
        if next_assigned_crm_user_id:
            user = user_repository.get_by_id(next_assigned_crm_user_id)
            if user is None or not _user_has_role(user, subtask.responsible_role_key):
                raise TaskValidationError("El usuario indicado no tiene el rol requerido para la siguiente subtarea.")
            return AssignmentResolution(next_assigned_crm_user_id, SubtaskStatus.ASSIGNED.value)
        return AssignmentResolution(None, SubtaskStatus.PENDING_ASSIGNMENT.value)


class DefaultUserAssignmentStrategy(NextAssignmentStrategy):
    def resolve(
        self,
        subtask: Subtask,
        next_assigned_crm_user_id: str | None,
        user_repository: CrmUserRepository,
    ) -> AssignmentResolution:
        assignee = next_assigned_crm_user_id or subtask.default_responsible_crm_user_id
        if assignee is None:
            raise TaskValidationError("La subtarea siguiente requiere un usuario responsable por defecto.")
        user = user_repository.get_by_id(assignee)
        if user is None or not _user_has_role(user, subtask.responsible_role_key):
            raise TaskValidationError("El usuario por defecto no tiene el rol requerido para la siguiente subtarea.")
        return AssignmentResolution(assignee, SubtaskStatus.ASSIGNED.value)


class ManualAssignmentStrategy(NextAssignmentStrategy):
    def resolve(
        self,
        subtask: Subtask,
        next_assigned_crm_user_id: str | None,
        user_repository: CrmUserRepository,
    ) -> AssignmentResolution:
        if not next_assigned_crm_user_id:
            raise TaskValidationError("Debe indicar el usuario responsable de la siguiente subtarea.")
        user = user_repository.get_by_id(next_assigned_crm_user_id)
        if user is None or not _user_has_role(user, subtask.responsible_role_key):
            raise TaskValidationError("El usuario indicado no tiene el rol requerido para la siguiente subtarea.")
        return AssignmentResolution(next_assigned_crm_user_id, SubtaskStatus.ASSIGNED.value)


class NextAssignmentStrategyRegistry:
    """Resolve next-subtask assignment strategies."""

    def __init__(self) -> None:
        self._strategies = {
            NextAssignmentPolicy.ROLE_QUEUE_AUTO.value: RoleQueueAssignmentStrategy(),
            NextAssignmentPolicy.DEFAULT_USER_AUTO.value: DefaultUserAssignmentStrategy(),
            NextAssignmentPolicy.MANUAL_REQUIRED.value: ManualAssignmentStrategy(),
        }

    def get(self, policy: str) -> NextAssignmentStrategy:
        strategy = self._strategies.get(policy)
        if strategy is None:
            raise TaskValidationError(f"Política de asignación no soportada: '{policy}'.")
        return strategy