"""Validation chains for subtask actions."""

from __future__ import annotations

from dataclasses import dataclass

from crm_backend.core.exceptions import TaskAccessDeniedError, TaskConflictError, TaskValidationError
from crm_backend.models.task_execution import Subtask, Task
from crm_backend.repositories import CrmUserRepository
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.tasks.states import get_subtask_state
from crm_backend.services.tasks.strategies import NextAssignmentStrategyRegistry, SubtaskItemValueStrategyRegistry


@dataclass(slots=True)
class ActionValidationContext:
    actor: ResolvedCrmSession
    task: Task
    subtask: Subtask
    action: str
    comment: str | None
    next_assigned_crm_user_id: str | None


class ValidationHandler:
    """Chain of responsibility base class."""

    def __init__(self, next_handler: ValidationHandler | None = None) -> None:
        self._next_handler = next_handler

    def set_next(self, next_handler: ValidationHandler) -> ValidationHandler:
        self._next_handler = next_handler
        return next_handler

    def validate(self, context: ActionValidationContext) -> None:
        self._validate(context)
        if self._next_handler is not None:
            self._next_handler.validate(context)

    def _validate(self, context: ActionValidationContext) -> None:
        raise NotImplementedError


class ActorPermissionValidator(ValidationHandler):
    def _validate(self, context: ActionValidationContext) -> None:
        actor = context.actor
        if "admin" in actor.role_keys:
            return
        if context.subtask.assigned_crm_user_id != actor.crm_user.crm_user_id:
            raise TaskAccessDeniedError("La subtarea solo puede ser operada por el usuario actualmente asignado.")


class StateActionValidator(ValidationHandler):
    def _validate(self, context: ActionValidationContext) -> None:
        get_subtask_state(context.subtask.status).ensure_action_allowed(context.action)


class RequiredCommentValidator(ValidationHandler):
    def _validate(self, context: ActionValidationContext) -> None:
        if not (context.comment or "").strip():
            raise TaskValidationError("Debe ingresar un comentario obligatorio para ejecutar la acción.")


class RequiredItemsCompletedValidator(ValidationHandler):
    def __init__(self, item_registry: SubtaskItemValueStrategyRegistry, next_handler: ValidationHandler | None = None) -> None:
        super().__init__(next_handler)
        self._item_registry = item_registry

    def _validate(self, context: ActionValidationContext) -> None:
        for item in context.subtask.items:
            if not item.is_required:
                continue
            strategy = self._item_registry.get(item.item_type)
            if not strategy.is_completed(item):
                raise TaskValidationError(
                    f"No se puede cerrar la subtarea porque falta completar el item obligatorio '{item.item_label}'."
                )


class NextAssignmentValidator(ValidationHandler):
    def __init__(
        self,
        assignment_registry: NextAssignmentStrategyRegistry,
        user_repository: CrmUserRepository,
        next_handler: ValidationHandler | None = None,
    ) -> None:
        super().__init__(next_handler)
        self._assignment_registry = assignment_registry
        self._user_repository = user_repository

    def _validate(self, context: ActionValidationContext) -> None:
        next_subtask = next((item for item in context.task.subtasks if item.order_index == context.subtask.order_index + 1), None)
        if next_subtask is None:
            return
        strategy = self._assignment_registry.get(next_subtask.next_assignment_policy)
        strategy.resolve(next_subtask, context.next_assigned_crm_user_id, self._user_repository)


class TransitionIntegrityValidator(ValidationHandler):
    def _validate(self, context: ActionValidationContext) -> None:
        if context.task.current_subtask_id != context.subtask.subtask_id and "admin" not in context.actor.role_keys:
            raise TaskConflictError("La subtarea indicada no es la subtarea activa de la tarea.")