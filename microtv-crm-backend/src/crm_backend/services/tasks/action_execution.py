"""Template method executors for subtask actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from crm_backend.core.exceptions import TaskAccessDeniedError, TaskValidationError
from crm_backend.models import SubtaskAssignment, SubtaskTransition, TaskAuditEvent, TaskComment
from crm_backend.models import TaskAttachment
from crm_backend.models.task_execution import Subtask, SubtaskStatus, Task, TaskCommentType, TaskStatus
from crm_backend.repositories import CrmUserRepository, TaskRepository
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.tasks.strategies import NextAssignmentStrategyRegistry
from crm_backend.services.tasks.validators import ActionValidationContext, ValidationHandler


@dataclass(slots=True)
class ActionExecutionContext:
    actor: ResolvedCrmSession
    task: Task
    subtask: Subtask
    comment: str
    next_assigned_crm_user_id: str | None
    attachment_ids: list[str]


class AdvanceTaskFlowService:
    """Unlock and assign the next subtask when the current one completes."""

    def __init__(
        self,
        task_repository: TaskRepository,
        user_repository: CrmUserRepository,
        assignment_registry: NextAssignmentStrategyRegistry,
    ) -> None:
        self._task_repository = task_repository
        self._user_repository = user_repository
        self._assignment_registry = assignment_registry

    def advance_after_close(self, context: ActionExecutionContext) -> None:
        current = context.subtask
        task = context.task
        next_subtask = next((item for item in task.subtasks if item.order_index == current.order_index + 1), None)
        if next_subtask is None:
            executive_candidates = self._user_repository.list_active_by_role_key("ejecutivo")
            if not executive_candidates:
                executive_candidates = self._user_repository.list_active_by_role_key("admin")
            if not executive_candidates:
                raise TaskValidationError("No hay usuarios ejecutivos activos para aprobar el cierre final de la tarea.")

            task.status = TaskStatus.BLOCKED.value
            task.current_assigned_crm_user_id = executive_candidates[0].crm_user_id
            task.is_finalized = False
            task.finalized_at = None
            task.finalized_by_crm_user_id = None
            return

        strategy = self._assignment_registry.get(next_subtask.next_assignment_policy)
        resolution = strategy.resolve(next_subtask, context.next_assigned_crm_user_id, self._user_repository)
        next_subtask.assigned_crm_user_id = resolution.assignee_crm_user_id
        next_subtask.status = resolution.next_status
        task.current_assigned_crm_user_id = resolution.assignee_crm_user_id
        task.status = TaskStatus.IN_PROGRESS.value
        task.is_finalized = False

        if resolution.assignee_crm_user_id is not None:
            self._task_repository.session.add(
                SubtaskAssignment(
                    subtask_id=next_subtask.subtask_id,
                    assigned_crm_user_id=resolution.assignee_crm_user_id,
                    assigned_by_crm_user_id=context.actor.crm_user.crm_user_id,
                    notes="Asignación automática al desbloquear la siguiente subtarea.",
                )
            )


class BaseSubtaskActionExecutor:
    """Shared execution algorithm for close/reject/on_hold actions."""

    action_name: str
    target_status: str
    audit_event_type: str

    def __init__(
        self,
        task_repository: TaskRepository,
        validator: ValidationHandler,
        flow_service: AdvanceTaskFlowService,
    ) -> None:
        self._task_repository = task_repository
        self._validator = validator
        self._flow_service = flow_service

    def execute(self, context: ActionExecutionContext) -> Task:
        validation_context = ActionValidationContext(
            actor=context.actor,
            task=context.task,
            subtask=context.subtask,
            action=self.action_name,
            comment=context.comment,
            next_assigned_crm_user_id=context.next_assigned_crm_user_id,
        )
        self._validator.validate(validation_context)
        comment = self._persist_comment(context)
        self._apply_action(context)
        self._persist_transition(context, comment.task_comment_id)
        self._persist_audit_event(context)
        self._after_action(context)
        return self._task_repository.save(context.task)

    def _persist_comment(self, context: ActionExecutionContext) -> TaskComment:
        comment = TaskComment(
            task_id=context.task.task_id,
            subtask_id=context.subtask.subtask_id,
            author_crm_user_id=context.actor.crm_user.crm_user_id,
            comment_type=TaskCommentType.TRANSITION.value,
            body=context.comment.strip(),
        )
        self._task_repository.session.add(comment)
        self._task_repository.session.flush()
        self._attach_pending_attachments(context, comment)
        return comment

    def _attach_pending_attachments(self, context: ActionExecutionContext, comment: TaskComment) -> None:
        if not context.attachment_ids:
            return

        attachments = list(
            self._task_repository.session.scalars(
                select(TaskAttachment).where(TaskAttachment.attachment_id.in_(context.attachment_ids))
            ).all()
        )
        if len(attachments) != len(set(context.attachment_ids)):
            raise TaskValidationError("Uno o más adjuntos indicados no existen.")

        for attachment in attachments:
            if attachment.task_id != context.task.task_id or attachment.subtask_id != context.subtask.subtask_id:
                raise TaskValidationError("Los adjuntos deben pertenecer a la misma tarea y subtarea del comentario.")
            if attachment.uploaded_by_crm_user_id != context.actor.crm_user.crm_user_id and "admin" not in context.actor.role_keys:
                raise TaskAccessDeniedError("No podés asociar adjuntos subidos por otro usuario.")
            if attachment.task_comment_id is not None:
                raise TaskValidationError("Uno de los adjuntos ya fue asociado a otro comentario.")

            attachment.task_comment_id = comment.task_comment_id

    def _persist_transition(self, context: ActionExecutionContext, task_comment_id: str | None) -> None:
        self._task_repository.session.add(
            SubtaskTransition(
                subtask_id=context.subtask.subtask_id,
                task_id=context.task.task_id,
                from_status=context.subtask.status_before_transition,
                to_status=context.subtask.status,
                action=self.action_name,
                performed_by_crm_user_id=context.actor.crm_user.crm_user_id,
                task_comment_id=task_comment_id,
            )
        )

    def _persist_audit_event(self, context: ActionExecutionContext) -> None:
        self._task_repository.session.add(
            TaskAuditEvent(
                task_id=context.task.task_id,
                subtask_id=context.subtask.subtask_id,
                event_type=self.audit_event_type,
                actor_crm_user_id=context.actor.crm_user.crm_user_id,
                payload_json={
                    "action": self.action_name,
                    "result_status": context.subtask.status,
                    "next_assigned_crm_user_id": context.next_assigned_crm_user_id,
                    "attachment_ids": context.attachment_ids,
                },
            )
        )

    def _apply_action(self, context: ActionExecutionContext) -> None:
        context.subtask.status_before_transition = context.subtask.status
        context.subtask.status = self.target_status
        context.subtask.closed_by_crm_user_id = context.actor.crm_user.crm_user_id
        if self.target_status == SubtaskStatus.COMPLETED.value:
            context.subtask.is_completed = True
            context.subtask.completion_notes = context.comment.strip()
            context.subtask.completed_at = datetime.now(UTC)
        else:
            context.subtask.is_completed = False
            context.subtask.completed_at = None

    def _after_action(self, context: ActionExecutionContext) -> None:
        raise NotImplementedError


class CloseSubtaskActionExecutor(BaseSubtaskActionExecutor):
    action_name = "close_subtask"
    target_status = SubtaskStatus.COMPLETED.value
    audit_event_type = "subtask.closed"

    def _after_action(self, context: ActionExecutionContext) -> None:
        self._flow_service.advance_after_close(context)


class RejectSubtaskActionExecutor(BaseSubtaskActionExecutor):
    action_name = "reject_subtask"
    target_status = SubtaskStatus.REJECTED.value
    audit_event_type = "subtask.rejected"

    def _after_action(self, context: ActionExecutionContext) -> None:
        context.task.status = TaskStatus.BLOCKED.value
        context.task.current_assigned_crm_user_id = context.subtask.assigned_crm_user_id
        context.task.is_finalized = False


class PutOnHoldSubtaskActionExecutor(BaseSubtaskActionExecutor):
    action_name = "put_on_hold"
    target_status = SubtaskStatus.ON_HOLD.value
    audit_event_type = "subtask.on_hold"

    def _after_action(self, context: ActionExecutionContext) -> None:
        context.task.status = TaskStatus.BLOCKED.value
        context.task.current_assigned_crm_user_id = context.subtask.assigned_crm_user_id
        context.task.is_finalized = False