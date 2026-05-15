"""Application services for the task module."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import select

from crm_backend.core.exceptions import TaskAccessDeniedError, TaskConflictError, TaskNotFoundError, TaskTemplateNotFoundError, TaskValidationError, SubtaskNotFoundError
from crm_backend.core.exceptions import InvalidTaskAttachmentError, TaskAttachmentNotFoundError
from crm_backend.infrastructure.task_media_storage import StoredTaskMedia, TaskMediaStorageFacade
from crm_backend.models import (
    NextAssignmentPolicy,
    Subtask,
    SubtaskAssignment,
    SubtaskType,
    TaskAttachment,
    TaskAttachmentType,
    SubtaskItemValue,
    SubtaskStatus,
    SubtaskTransition,
    Task,
    TaskAuditEvent,
    TaskComment,
    TaskCommentMention,
    TaskCommentType,
    Location,
    StockProduct,
    TaskExtraMaterial,
    TaskPreFormInstance,
    TaskStatus,
    TaskTemplate,
    TaskTemplateItem,
    TaskTemplatePreForm,
    TaskTemplatePreFormField,
    TaskTemplateSubtask,
    TemplateItemType,
    TransitionAction,
)
from crm_backend.repositories import CrmUserRepository, TaskRepository, TaskTemplateRepository
from crm_backend.schemas.tasks import (
    ApproveTaskRequest,
    CreateTaskFromTemplateRequest,
    CreateTaskTemplateRequest,
    ExecuteSubtaskActionRequest,
    RejectTaskApprovalRequest,
    SetTaskTemplateActivationRequest,
    UpdateTaskTemplateRequest,
    UpdateSubtaskProgressRequest,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.notification_service import NotificationService
from crm_backend.models.notification import NotificationEntityType, NotificationType
from crm_backend.services.tasks.action_execution import (
    ActionExecutionContext,
    AdvanceTaskFlowService,
    CloseSubtaskActionExecutor,
    PutOnHoldSubtaskActionExecutor,
    RejectSubtaskActionExecutor,
)
from crm_backend.services.tasks.states import get_subtask_state
from crm_backend.services.tasks.strategies import NextAssignmentStrategyRegistry, SubtaskItemValueStrategyRegistry
from crm_backend.services.tasks.validators import (
    ActorPermissionValidator,
    NextAssignmentValidator,
    PendingInventoryRequestsResolvedValidator,
    RequiredCommentValidator,
    RequiredItemsCompletedValidator,
    StateActionValidator,
    TransitionIntegrityValidator,
)
from crm_backend.services.permission_service import PERMISSION_TICKET_REASSIGN, PermissionService
from crm_backend.services.material_flow_service import TaskMaterialFlowFacade


class TaskBuilder:
    """Builder/assembler that materializes a task from a template."""

    def build(self, template: TaskTemplate, actor: ResolvedCrmSession, payload: CreateTaskFromTemplateRequest) -> Task:
        task = Task(
            client_id=payload.client_id,
            location_id=payload.location_id,
            template_id=template.template_id,
            task_title=(payload.task_title or template.template_name).strip(),
            task_description=payload.task_description if payload.task_description is not None else template.description,
            status=TaskStatus.PENDING.value,
            requires_arrival_comment=(
                template.requires_arrival_comment if payload.requires_arrival_comment is None else bool(payload.requires_arrival_comment)
            ),
            requires_video_evidence=(
                template.requires_video_evidence if payload.requires_video_evidence is None else bool(payload.requires_video_evidence)
            ),
            created_by_crm_user_id=actor.crm_user.crm_user_id,
        )

        ordered_subtasks = sorted(template.subtasks, key=lambda item: item.order_index)
        has_pre_form_subtask = any(
            (item.subtask_type or SubtaskType.STANDARD.value) == SubtaskType.PRE_FORM.value
            for item in ordered_subtasks
        )
        for index, template_subtask in enumerate(ordered_subtasks):
            status = SubtaskStatus.LOCKED.value
            assigned_crm_user_id = None
            subtask_type = template_subtask.subtask_type or SubtaskType.STANDARD.value
            if index == 0 and not has_pre_form_subtask and subtask_type != SubtaskType.PRE_FORM.value:
                assigned_crm_user_id = template_subtask.default_responsible_crm_user_id
                status = (
                    SubtaskStatus.ASSIGNED.value
                    if assigned_crm_user_id is not None
                    else SubtaskStatus.PENDING_ASSIGNMENT.value
                )

            subtask = Subtask(
                subtask_id=str(uuid4()),
                template_subtask_id=template_subtask.template_subtask_id,
                subtask_title=template_subtask.subtask_title,
                subtask_description=template_subtask.subtask_description,
                order_index=template_subtask.order_index,
                responsible_role_key=template_subtask.responsible_role_key,
                assigned_crm_user_id=assigned_crm_user_id,
                default_responsible_crm_user_id=template_subtask.default_responsible_crm_user_id,
                close_comment_required=template_subtask.close_comment_required,
                requires_arrival_comment=template_subtask.requires_arrival_comment,
                requires_video_evidence=template_subtask.requires_video_evidence,
                next_assignment_policy=template_subtask.next_assignment_policy,
                subtask_type=subtask_type,
                status=status,
            )
            for template_item in sorted(template_subtask.items, key=lambda item: item.item_order):
                subtask.items.append(
                    SubtaskItemValue(
                        template_checklist_item_id=template_item.template_checklist_item_id,
                        item_label=template_item.item_label,
                        item_order=template_item.item_order,
                        item_type=template_item.item_type,
                        is_required=template_item.is_required,
                    )
                )
            if index == 0 and not has_pre_form_subtask and subtask_type != SubtaskType.PRE_FORM.value:
                task.current_assigned_crm_user_id = assigned_crm_user_id
                task.status = TaskStatus.IN_PROGRESS.value
            task.subtasks.append(subtask)
        return task


_logger = logging.getLogger(__name__)


class TaskApplicationService:
    """Orchestrate the task template and execution flows."""

    def __init__(
        self,
        template_repository: TaskTemplateRepository,
        task_repository: TaskRepository,
        user_repository: CrmUserRepository,
        task_media_storage: TaskMediaStorageFacade,
        task_material_flow: TaskMaterialFlowFacade,
        notification_service: NotificationService | None = None,
        permission_service: PermissionService | None = None,
        activity_log_service: ActivityLogService | None = None,
    ) -> None:
        self._template_repository = template_repository
        self._task_repository = task_repository
        self._user_repository = user_repository
        self._task_media_storage = task_media_storage
        self._task_material_flow = task_material_flow
        self._notification_service = notification_service
        self._permission_service = permission_service
        self._activity_log_service = activity_log_service
        self._task_builder = TaskBuilder()
        self._item_strategy_registry = SubtaskItemValueStrategyRegistry()
        self._assignment_strategy_registry = NextAssignmentStrategyRegistry()

    def create_template(self, actor: ResolvedCrmSession, payload: CreateTaskTemplateRequest) -> TaskTemplate:
        self._ensure_admin_or_executive(actor)
        template = TaskTemplate(
            is_active=True,
            template_name=payload.template_name.strip(),
            description=payload.description,
            requires_arrival_comment=self._template_requires_arrival(payload),
            requires_video_evidence=self._template_requires_video(payload),
            requires_pre_form=bool(payload.requires_pre_form),
            created_by_crm_user_id=actor.crm_user.crm_user_id,
        )
        self._apply_template_payload(template, payload)
        self._task_material_flow.sync_template_materials(template, payload)
        return self._template_repository.save(template)

    def get_template_detail(self, actor: ResolvedCrmSession, template_id: str) -> TaskTemplate:
        self._ensure_read_access(actor)
        template = self._template_repository.get_by_id(template_id)
        if template is None:
            raise TaskTemplateNotFoundError()
        return template

    def update_template(self, actor: ResolvedCrmSession, template_id: str, payload: UpdateTaskTemplateRequest) -> TaskTemplate:
        self._ensure_admin_or_executive(actor)
        template = self._template_repository.get_by_id(template_id)
        if template is None:
            raise TaskTemplateNotFoundError()

        template.template_name = payload.template_name.strip()
        template.description = payload.description
        template.requires_arrival_comment = self._template_requires_arrival(payload)
        template.requires_video_evidence = self._template_requires_video(payload)
        template.requires_pre_form = bool(payload.requires_pre_form)
        template.subtasks.clear()
        self._apply_template_payload(template, payload)
        self._task_material_flow.sync_template_materials(template, payload)
        return self._template_repository.save(template)

    def set_template_active(
        self,
        actor: ResolvedCrmSession,
        template_id: str,
        payload: SetTaskTemplateActivationRequest,
    ) -> TaskTemplate:
        self._ensure_admin_or_executive(actor)
        template = self._template_repository.get_by_id(template_id)
        if template is None:
            raise TaskTemplateNotFoundError()

        template.is_active = payload.is_active
        return self._template_repository.save(template)

    def list_templates(self, actor: ResolvedCrmSession) -> list[TaskTemplate]:
        self._ensure_read_access(actor)
        try:
            include_inactive = bool({"admin", "ejecutivo"}.intersection(actor.role_keys))
            return self._template_repository.list(include_inactive=include_inactive)
        except Exception:
            _logger.exception("Failed to list task templates for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def _apply_template_payload(self, template: TaskTemplate, payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest) -> None:
        if template.requires_pre_form:
            pre_form = template.pre_form or TaskTemplatePreForm()
            pre_form_payload = payload.pre_form

            if pre_form_payload is not None:
                pre_form.title = (pre_form_payload.title or "").strip() or None
                pre_form.instructions = (pre_form_payload.instructions or "").strip() or None
            else:
                pre_form.title = None
                pre_form.instructions = None

            pre_form.fields.clear()

            if pre_form_payload is not None:
                for field_payload in sorted(pre_form_payload.fields, key=lambda item: item.order_index):
                    pre_form.fields.append(
                        TaskTemplatePreFormField(
                            label=field_payload.label.strip(),
                            field_type=field_payload.field_type,
                            is_required=bool(field_payload.is_required),
                            order_index=field_payload.order_index,
                            placeholder=(field_payload.placeholder or "").strip() or None,
                        )
                    )

            template.pre_form = pre_form
        else:
            template.pre_form = None

        if template.requires_pre_form:
            template.subtasks.append(
                TaskTemplateSubtask(
                    subtask_title="Formulario previo del cliente",
                    subtask_description="El cliente completa este formulario antes de iniciar el trabajo.",
                    order_index=0,
                    responsible_role_key="ejecutivo",
                    default_responsible_crm_user_id=None,
                    close_comment_required=False,
                    requires_arrival_comment=False,
                    requires_video_evidence=False,
                    next_assignment_policy=NextAssignmentPolicy.MANUAL_REQUIRED.value,
                    subtask_type=SubtaskType.PRE_FORM.value,
                )
            )

        ordered_payload_subtasks = sorted(payload.subtasks, key=lambda item: item.order_index)
        self._apply_legacy_template_rules(payload, ordered_payload_subtasks)
        order_offset = 1 if template.requires_pre_form else 0
        for user_subtask_index, subtask_payload in enumerate(ordered_payload_subtasks):
            self._validate_default_user(subtask_payload.default_responsible_crm_user_id, subtask_payload.responsible_role_key)
            template_subtask = TaskTemplateSubtask(
                subtask_title=subtask_payload.subtask_title.strip(),
                subtask_description=subtask_payload.subtask_description,
                order_index=user_subtask_index + order_offset,
                responsible_role_key=subtask_payload.responsible_role_key,
                default_responsible_crm_user_id=subtask_payload.default_responsible_crm_user_id,
                close_comment_required=subtask_payload.close_comment_required,
                requires_arrival_comment=bool(subtask_payload.requires_arrival_comment),
                requires_video_evidence=bool(subtask_payload.requires_video_evidence),
                next_assignment_policy=subtask_payload.next_assignment_policy,
                subtask_type=(
                    SubtaskType.STANDARD.value
                    if template.requires_pre_form and subtask_payload.subtask_type == SubtaskType.PRE_FORM.value
                    else subtask_payload.subtask_type
                ),
            )
            for item_payload in sorted(subtask_payload.items, key=lambda item: item.item_order):
                template_subtask.items.append(
                    TaskTemplateItem(
                        item_label=item_payload.item_label.strip(),
                        item_order=item_payload.item_order,
                        item_type=item_payload.item_type,
                        is_required=item_payload.is_required,
                    )
                )
            template.subtasks.append(template_subtask)

        template.requires_arrival_comment = any(item.requires_arrival_comment for item in template.subtasks)
        template.requires_video_evidence = any(item.requires_video_evidence for item in template.subtasks)

    def _template_requires_arrival(self, payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest) -> bool:
        if self._payload_has_explicit_subtask_rules(payload):
            return any(subtask.requires_arrival_comment for subtask in payload.subtasks)
        return bool(payload.requires_arrival_comment)

    def _template_requires_video(self, payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest) -> bool:
        if self._payload_has_explicit_subtask_rules(payload):
            return any(subtask.requires_video_evidence for subtask in payload.subtasks)
        return bool(payload.requires_video_evidence)

    def _payload_has_explicit_subtask_rules(self, payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest) -> bool:
        return any(
            "requires_arrival_comment" in subtask.model_fields_set
            or "requires_video_evidence" in subtask.model_fields_set
            for subtask in payload.subtasks
        )

    def _apply_legacy_template_rules(
        self,
        payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest,
        ordered_subtasks: list,
    ) -> None:
        if self._payload_has_explicit_subtask_rules(payload):
            return
        if not ordered_subtasks:
            return

        final_subtask = ordered_subtasks[-1]
        if payload.requires_arrival_comment:
            final_subtask.requires_arrival_comment = True
        if payload.requires_video_evidence:
            final_subtask.requires_video_evidence = True

    def create_task_from_template(self, actor: ResolvedCrmSession, payload: CreateTaskFromTemplateRequest) -> Task:
        self._ensure_admin_or_executive(actor)
        template = self._template_repository.get_by_id(payload.template_id)
        if template is None or not template.is_active:
            raise TaskTemplateNotFoundError()

        task = self._task_builder.build(template, actor, payload)
        if template.requires_pre_form and template.pre_form is not None:
            task.pre_form_instances.append(
                TaskPreFormInstance(
                    template_pre_form_id=template.pre_form.form_id,
                    token_hash=self._hash_token(secrets.token_urlsafe(48)),
                    expires_at=datetime.now(UTC) + timedelta(hours=72),
                )
            )
        self._task_material_flow.materialize_task_requirements(task, template)
        self._append_extra_materials(task, payload)
        for subtask in task.subtasks:
            if subtask.assigned_crm_user_id is None:
                continue
            subtask.assignments.append(
                SubtaskAssignment(
                    assigned_crm_user_id=subtask.assigned_crm_user_id,
                    assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                    notes="Asignación inicial desde template.",
                )
            )
        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.created_from_template",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={"template_id": template.template_id, "client_id": task.client_id, "location_id": task.location_id},
            )
        )
        saved_task = self._task_repository.save(task)
        self._notify_task_creation_state(saved_task)
        return saved_task

    def list_tasks_assigned_to_actor(self, actor: ResolvedCrmSession) -> list[Task]:
        self._ensure_read_access(actor)
        try:
            return self._task_repository.list_tasks_assigned_to_user(actor.crm_user.crm_user_id)
        except Exception:
            _logger.exception("Failed to list assigned tasks for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_tracking_tasks_for_actor(self, actor: ResolvedCrmSession) -> list[Task]:
        self._ensure_read_access(actor)
        try:
            if {"admin", "ejecutivo"}.intersection(actor.role_keys):
                return self._task_repository.list_tracking_tasks_for_all_roles()

            visible_roles = [role for role in actor.role_keys if role in {"deposito", "tecnico"}]
            if not visible_roles:
                return []
            return self._task_repository.list_tracking_tasks_for_roles(visible_roles)
        except Exception:
            _logger.exception("Failed to list tracking tasks for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_task_history_for_actor(self, actor: ResolvedCrmSession) -> list[Task]:
        self._ensure_admin_or_executive(actor)
        try:
            return self._task_repository.list_completed_tasks()
        except Exception:
            _logger.exception("Failed to list task history for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_unassigned_subtasks_for_actor(self, actor: ResolvedCrmSession) -> list[Subtask]:
        self._ensure_read_access(actor)
        try:
            visible_roles = [role for role in actor.role_keys if role in {"deposito", "tecnico"}]
            if "admin" in actor.role_keys:
                visible_roles = ["deposito", "tecnico", "ejecutivo", "admin"]
            return self._task_repository.list_unassigned_subtasks_for_roles(visible_roles)
        except Exception:
            _logger.exception("Failed to list unassigned subtasks for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def get_task_detail(self, actor: ResolvedCrmSession, task_id: str) -> Task:
        self._ensure_read_access(actor)
        task = self._task_repository.get_task_detail(task_id)
        if task is None:
            raise TaskNotFoundError()
        if "admin" in actor.role_keys or "ejecutivo" in actor.role_keys:
            return task
        actor_id = actor.crm_user.crm_user_id
        if task.current_assigned_crm_user_id == actor_id:
            return task
        if any(subtask.responsible_role_key in actor.role_keys for subtask in task.subtasks):
            return task
        raise TaskAccessDeniedError("El usuario no puede consultar esta tarea.")

    def add_task_comment(
        self,
        actor: ResolvedCrmSession,
        task_id: str,
        *,
        body: str,
        location_id: str | None,
        attachment_ids: list[str],
        mentioned_user_ids: list[str] | None = None,
        comment_type: str = TaskCommentType.GENERAL.value,
    ) -> Task:
        task = self.get_task_detail(actor, task_id)
        self._ensure_task_operable(actor, task)

        normalized_body = body.strip()
        if not normalized_body:
            raise TaskValidationError("El comentario no puede estar vacío.")

        resolved_location_id: str | None = None
        if location_id:
            location = self._task_repository.session.get(Location, location_id)
            if location is None:
                raise TaskValidationError("La ubicación indicada para el comentario no existe.")
            resolved_location_id = location.location_id

        comment = TaskComment(
            task_id=task.task_id,
            subtask_id=task.current_subtask_id,
            author_crm_user_id=actor.crm_user.crm_user_id,
            location_id=resolved_location_id,
            comment_type=comment_type,
            body=normalized_body,
        )
        task.comments.append(comment)
        self._attach_files_to_comment(task, comment, attachment_ids, actor)
        mentioned_users = self._resolve_mentioned_users(mentioned_user_ids or [])
        for mentioned_user in mentioned_users:
            comment.mentions.append(
                TaskCommentMention(
                    mentioned_crm_user_id=mentioned_user.crm_user_id,
                    created_by_crm_user_id=actor.crm_user.crm_user_id,
                )
            )
        self._try_register_arrival_from_comment(
            actor=actor,
            task=task,
            comment=comment,
            has_multimedia=bool(attachment_ids),
        )
        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.comment_added",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "comment_type": comment_type,
                    "task_comment_id": comment.task_comment_id,
                    "location_id": resolved_location_id,
                },
            )
        )
        for mentioned_user in mentioned_users:
            self._log_comment_mention(actor, task, comment, mentioned_user)
        saved_task = self._task_repository.save(task)
        try:
            if self._notification_service is not None:
                actor_name = actor.crm_user.display_name or actor.crm_user.email or actor.crm_user.crm_user_id
                task_label = saved_task.task_title
                for mentioned_user in mentioned_users:
                    self._notification_service.notify(
                        recipient_crm_user_id=mentioned_user.crm_user_id,
                        notification_type=NotificationType.TASK_COMMENT_MENTIONED,
                        title=f"Te mencionaron en tarea '{task_label}'",
                        body=f"{actor_name} te mencionó en un comentario de la tarea '{task_label}'.",
                        entity_type=NotificationEntityType.TASK,
                        entity_id=saved_task.task_id,
                        metadata={
                            "comment_id": comment.task_comment_id,
                            "mentioned_by_crm_user_id": actor.crm_user.crm_user_id,
                            "subtask_id": comment.subtask_id,
                        },
                    )
        except Exception:
            _logger.exception("Error sending task comment mention notification for task %s", saved_task.task_id)
        return saved_task

    def claim_unassigned_subtask(self, actor: ResolvedCrmSession, subtask_id: str) -> Task:
        self._ensure_read_access(actor)
        subtask = self._task_repository.get_subtask_detail(subtask_id)
        if subtask is None:
            raise SubtaskNotFoundError()
        if subtask.status != SubtaskStatus.PENDING_ASSIGNMENT.value:
            raise TaskConflictError("La subtarea ya no está disponible para ser tomada.")
        if "admin" not in actor.role_keys and subtask.responsible_role_key not in actor.role_keys:
            raise TaskAccessDeniedError("Solo usuarios del rol correcto pueden tomar esta subtarea.")

        subtask.assigned_crm_user_id = actor.crm_user.crm_user_id
        previous_status = subtask.status
        subtask.status = SubtaskStatus.ASSIGNED.value
        subtask.assignments.append(
            SubtaskAssignment(
                assigned_crm_user_id=actor.crm_user.crm_user_id,
                assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                notes="Subtarea tomada desde la bandeja sin asignar.",
            )
        )
        subtask.transitions.append(
            SubtaskTransition(
                task_id=subtask.task_id,
                from_status=previous_status,
                to_status=subtask.status,
                action=TransitionAction.CLAIM_SUBTASK.value,
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
            )
        )
        subtask.task.current_assigned_crm_user_id = actor.crm_user.crm_user_id
        subtask.task.audit_events.append(
            TaskAuditEvent(
                subtask_id=subtask.subtask_id,
                event_type="subtask.claimed",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={"subtask_id": subtask.subtask_id},
            )
        )
        return self._task_repository.save(subtask.task)

    def assign_subtask(
        self,
        actor: ResolvedCrmSession,
        subtask_id: str,
        assigned_crm_user_id: str,
        notes: str | None,
    ) -> Task:
        subtask = self._task_repository.get_subtask_detail(subtask_id)
        if subtask is None:
            raise SubtaskNotFoundError()
        self._ensure_assignment_access(actor, subtask)

        if subtask.status not in {
            SubtaskStatus.PENDING_ASSIGNMENT.value,
            SubtaskStatus.ASSIGNED.value,
            SubtaskStatus.IN_PROGRESS.value,
        }:
            raise TaskConflictError("Solo se pueden asignar o reasignar subtareas activas.")

        try:
            UUID(str(assigned_crm_user_id))
        except (TypeError, ValueError):
            raise TaskValidationError("El identificador del usuario a asignar tiene un formato inválido.") from None

        target_user = self._user_repository.get_by_id(assigned_crm_user_id)
        if target_user is None:
            raise TaskValidationError("El usuario indicado no existe.")

        valid_role_keys = {
            subtask.responsible_role_key,
            {"admin": "admin_crm", "deposito": "encargado_deposito", "tecnico": "tecnico_campo"}.get(
                subtask.responsible_role_key,
                subtask.responsible_role_key,
            ),
        }
        if not any(
            assignment.role is not None and assignment.role.role_key in valid_role_keys
            for assignment in target_user.assigned_roles
        ):
            raise TaskValidationError("El usuario indicado no tiene el rol requerido para esta subtarea.")

        previous_assigned_crm_user_id = subtask.assigned_crm_user_id
        if previous_assigned_crm_user_id == assigned_crm_user_id:
            raise TaskValidationError("La subtarea ya está asignada al usuario seleccionado.")

        previous_status = subtask.status
        subtask.assigned_crm_user_id = assigned_crm_user_id
        if subtask.status == SubtaskStatus.PENDING_ASSIGNMENT.value:
            subtask.status = SubtaskStatus.ASSIGNED.value

        subtask.assignments.append(
            SubtaskAssignment(
                assigned_crm_user_id=assigned_crm_user_id,
                assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                notes=(notes or "Asignación manual de subtarea.").strip() or None,
            )
        )

        if previous_status != subtask.status:
            subtask.transitions.append(
                SubtaskTransition(
                    task_id=subtask.task_id,
                    from_status=previous_status,
                    to_status=subtask.status,
                    action=TransitionAction.ASSIGN_SUBTASK.value,
                    performed_by_crm_user_id=actor.crm_user.crm_user_id,
                )
            )

        if subtask.task.current_subtask_id == subtask.subtask_id:
            subtask.task.current_assigned_crm_user_id = assigned_crm_user_id

        subtask.task.audit_events.append(
            TaskAuditEvent(
                subtask_id=subtask.subtask_id,
                event_type="subtask.assigned_manually",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "subtask_id": subtask.subtask_id,
                    "previous_assigned_crm_user_id": previous_assigned_crm_user_id,
                    "assigned_crm_user_id": assigned_crm_user_id,
                    "previous_status": previous_status,
                    "current_status": subtask.status,
                },
            )
        )

        saved_task = self._task_repository.save(subtask.task)
        try:
            if self._notification_service is not None:
                is_reassignment = previous_assigned_crm_user_id is not None
                notif_type = NotificationType.TASK_SUBTASK_REASSIGNED if is_reassignment else NotificationType.TASK_SUBTASK_ASSIGNED
                self._notification_service.notify(
                    recipient_crm_user_id=assigned_crm_user_id,
                    notification_type=notif_type,
                    title="Subtarea asignada a vos",
                    body=f"La subtarea '{subtask.title}' de la tarea '{subtask.task.title}' está asignada a vos.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=subtask.task_id,
                )
        except Exception:
            _logger.exception("Error sending assign_subtask notification")
        return saved_task

    def approve_task(self, actor: ResolvedCrmSession, task_id: str, payload: ApproveTaskRequest) -> Task:
        self._ensure_admin_or_executive(actor)
        task = self._task_repository.get_task_detail(task_id)
        if task is None:
            raise TaskNotFoundError()
        if not self._is_task_pending_executive_approval(task):
            raise TaskConflictError("La tarea no está pendiente de aprobación ejecutiva.")
        if self._task_has_pending_required_arrival(task):
            raise TaskConflictError("Este pedido requiere llegada registrada antes de aprobar el cierre final.")
        if self._task_has_pending_required_closure_media(task):
            raise TaskConflictError("Este pedido requiere evidencia multimedia (foto o video) para aprobar el cierre final.")

        previous_assigned_crm_user_id = task.current_assigned_crm_user_id
        previous_subtask_id = task.current_subtask_id
        task.status = TaskStatus.COMPLETED.value
        task.current_assigned_crm_user_id = None
        task.is_finalized = True
        task.finalized_at = datetime.now(UTC)
        task.finalized_by_crm_user_id = actor.crm_user.crm_user_id
        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.approved_by_executive",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "task_id": task.task_id,
                    "previous_assigned_crm_user_id": previous_assigned_crm_user_id,
                    "previous_subtask_id": previous_subtask_id,
                },
            )
        )
        comment = (payload.comment or "").strip()
        if comment:
            task.comments.append(
                TaskComment(
                    task_id=task.task_id,
                    subtask_id=None,
                    author_crm_user_id=actor.crm_user.crm_user_id,
                    comment_type=TaskCommentType.CLOSURE.value,
                    body=comment,
                )
            )
        saved_task = self._task_repository.save(task)
        try:
            if self._notification_service is not None and previous_assigned_crm_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=previous_assigned_crm_user_id,
                    notification_type=NotificationType.TASK_APPROVED,
                    title=f"Tarea '{saved_task.title}' aprobada",
                    body=f"La tarea '{saved_task.title}' fue aprobada y marcada como completada por un ejecutivo.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=saved_task.task_id,
                )
        except Exception:
            _logger.exception("Error sending approve_task notification for task %s", saved_task.task_id)
        return saved_task

    def reject_task_approval(self, actor: ResolvedCrmSession, task_id: str, payload: RejectTaskApprovalRequest) -> Task:
        self._ensure_admin_or_executive(actor)
        task = self._task_repository.get_task_detail(task_id)
        if task is None:
            raise TaskNotFoundError()
        if not self._is_task_pending_executive_approval(task):
            raise TaskConflictError("La tarea no está pendiente de aprobación ejecutiva.")

        comment = payload.comment.strip()
        if not comment:
            raise TaskValidationError("El rechazo del cierre requiere un comentario obligatorio.")

        current_subtask = next((subtask for subtask in task.subtasks if subtask.subtask_id == task.current_subtask_id), None)
        if current_subtask is None or current_subtask.assigned_crm_user_id is None:
            current_subtask = next(
                (
                    subtask
                    for subtask in sorted(task.subtasks, key=lambda item: item.order_index, reverse=True)
                    if subtask.assigned_crm_user_id is not None
                ),
                None,
            )
        if current_subtask is None or current_subtask.assigned_crm_user_id is None:
            raise TaskConflictError("No se pudo determinar la subtarea operativa a devolver tras el rechazo.")

        previous_assigned_crm_user_id = task.current_assigned_crm_user_id
        task.status = TaskStatus.IN_PROGRESS.value
        task.current_assigned_crm_user_id = current_subtask.assigned_crm_user_id
        task.is_finalized = False
        task.finalized_at = None
        task.finalized_by_crm_user_id = None
        current_subtask.status_before_transition = current_subtask.status
        current_subtask.status = SubtaskStatus.IN_PROGRESS.value
        current_subtask.is_completed = False
        current_subtask.completed_at = None
        current_subtask.closed_by_crm_user_id = None
        current_subtask.completion_notes = None
        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.rejected_by_executive",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "task_id": task.task_id,
                    "previous_assigned_crm_user_id": previous_assigned_crm_user_id,
                    "returned_to_crm_user_id": current_subtask.assigned_crm_user_id,
                    "subtask_id": current_subtask.subtask_id,
                },
            )
        )
        task.comments.append(
            TaskComment(
                task_id=task.task_id,
                subtask_id=current_subtask.subtask_id,
                author_crm_user_id=actor.crm_user.crm_user_id,
                comment_type=TaskCommentType.TRANSITION.value,
                body=comment,
            )
        )
        saved_task = self._task_repository.save(task)
        try:
            if self._notification_service is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=current_subtask.assigned_crm_user_id,
                    notification_type=NotificationType.TASK_REJECTED,
                    title=f"Tarea '{saved_task.title}' rechazada por ejecutivo",
                    body="El cierre final de la tarea fue rechazado. Revisá el comentario del ejecutivo y retomá la subtarea.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=saved_task.task_id,
                )
        except Exception:
            _logger.exception("Error sending reject_task_approval notification for task %s", saved_task.task_id)
        return saved_task

    def update_subtask_progress(
        self,
        actor: ResolvedCrmSession,
        subtask_id: str,
        payload: UpdateSubtaskProgressRequest,
    ) -> Task:
        subtask = self._task_repository.get_subtask_detail(subtask_id)
        if subtask is None:
            raise SubtaskNotFoundError()
        task = subtask.task
        self._ensure_subtask_is_operable_by_actor(actor, subtask)
        get_subtask_state(subtask.status).ensure_action_allowed("update_items")

        item_map = {item.subtask_item_value_id: item for item in subtask.items}
        any_updated = False
        for item_payload in payload.items:
            item = item_map.get(item_payload.item_id)
            if item is None:
                raise TaskValidationError("El item indicado no pertenece a la subtarea.")
            strategy = self._item_strategy_registry.get(item.item_type)
            strategy.apply(item, item_payload.model_dump(exclude_unset=True), actor.crm_user.crm_user_id)
            any_updated = True

        if any_updated and subtask.status == SubtaskStatus.ASSIGNED.value:
            previous_status = subtask.status
            subtask.status = SubtaskStatus.IN_PROGRESS.value
            subtask.is_completed = False
            task.status = TaskStatus.IN_PROGRESS.value
            subtask.transitions.append(
                SubtaskTransition(
                    task_id=task.task_id,
                    from_status=previous_status,
                    to_status=subtask.status,
                    action=TransitionAction.START_SUBTASK.value,
                    performed_by_crm_user_id=actor.crm_user.crm_user_id,
                )
            )

        task.audit_events.append(
            TaskAuditEvent(
                subtask_id=subtask.subtask_id,
                event_type="subtask.progress_saved",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "updated_items": [item.item_id for item in payload.items],
                    "updated_item_payloads": [item.model_dump(exclude_unset=True) for item in payload.items],
                },
            )
        )
        return self._task_repository.save(task)

    def execute_subtask_action(
        self,
        actor: ResolvedCrmSession,
        subtask_id: str,
        payload: ExecuteSubtaskActionRequest,
    ) -> Task:
        subtask = self._task_repository.get_subtask_detail(subtask_id)
        if subtask is None:
            raise SubtaskNotFoundError()

        task = subtask.task
        self._ensure_subtask_is_operable_by_actor(actor, subtask)
        if payload.action == TransitionAction.CLOSE_SUBTASK.value:
            self._validate_task_close_requirements(task, subtask, payload.attachment_ids)
        flow_service = AdvanceTaskFlowService(
            self._task_repository,
            self._user_repository,
            self._assignment_strategy_registry,
        )
        base_chain = ActorPermissionValidator()
        base_chain.set_next(StateActionValidator()).set_next(RequiredCommentValidator()).set_next(
            TransitionIntegrityValidator()
        )

        executor_map = {
            TransitionAction.CLOSE_SUBTASK.value: CloseSubtaskActionExecutor(
                self._task_repository,
                self._build_close_validator_chain(base_chain),
                flow_service,
            ),
            TransitionAction.REJECT_SUBTASK.value: RejectSubtaskActionExecutor(
                self._task_repository,
                base_chain,
                flow_service,
            ),
            TransitionAction.PUT_ON_HOLD.value: PutOnHoldSubtaskActionExecutor(
                self._task_repository,
                base_chain,
                flow_service,
            ),
        }
        executor = executor_map[payload.action]
        saved_task = executor.execute(
            ActionExecutionContext(
                actor=actor,
                task=task,
                subtask=subtask,
                comment=payload.comment,
                next_assigned_crm_user_id=payload.next_assigned_crm_user_id,
                attachment_ids=payload.attachment_ids,
            )
        )
        if payload.action == TransitionAction.CLOSE_SUBTASK.value:
            self._notify_unlocked_subtask_state(saved_task, closed_subtask_id=subtask.subtask_id)
        return saved_task

    async def upload_task_attachments(
        self,
        actor: ResolvedCrmSession,
        task_id: str,
        subtask_id: str | None,
        files: list[UploadFile],
    ) -> list[TaskAttachment]:
        if not files:
            raise InvalidTaskAttachmentError("Se requiere al menos un archivo para subir multimedia.")

        task = self.get_task_detail(actor, task_id)
        subtask = None
        if subtask_id is not None:
            subtask = next((item for item in task.subtasks if item.subtask_id == subtask_id), None)
            if subtask is None:
                raise SubtaskNotFoundError()
            self._ensure_subtask_is_operable_by_actor(actor, subtask)

        stored_media_batch: list[StoredTaskMedia] = []
        persisted_attachments: list[TaskAttachment] = []
        try:
            for upload in files:
                stored_media = await self._task_media_storage.store(upload)
                stored_media_batch.append(stored_media)
                attachment = TaskAttachment(
                    task_id=task.task_id,
                    subtask_id=subtask.subtask_id if subtask is not None else None,
                    file_name=stored_media.file_name,
                    file_url=stored_media.file_url,
                    file_size_bytes=stored_media.file_size_bytes,
                    mime_type=stored_media.mime_type,
                    attachment_type=stored_media.attachment_type,
                    uploaded_by_crm_user_id=actor.crm_user.crm_user_id,
                )
                self._task_repository.session.add(attachment)
                persisted_attachments.append(attachment)

            self._task_repository.session.commit()
        except Exception:
            self._task_repository.session.rollback()
            for stored_media in stored_media_batch:
                self._task_media_storage.delete(stored_media)
            raise

        for attachment in persisted_attachments:
            self._task_repository.session.refresh(attachment)
        return persisted_attachments

    def delete_task_attachment(self, actor: ResolvedCrmSession, attachment_id: str) -> None:
        attachment = self._task_repository.get_attachment(attachment_id)
        if attachment is None:
            raise TaskAttachmentNotFoundError()
        if attachment.uploaded_by_crm_user_id != actor.crm_user.crm_user_id and "admin" not in actor.role_keys:
            raise TaskAccessDeniedError("No podés eliminar adjuntos subidos por otro usuario.")
        if attachment.task_comment_id is not None:
            raise TaskConflictError("El adjunto ya quedó asociado a un comentario persistido y no puede eliminarse.")

        self._task_media_storage.delete_from_persisted_values(
            attachment_type=attachment.attachment_type,
            file_name=attachment.file_name,
            file_url=attachment.file_url,
            mime_type=attachment.mime_type,
            file_size_bytes=attachment.file_size_bytes,
        )
        self._task_repository.session.delete(attachment)
        self._task_repository.session.commit()

    def _attach_files_to_comment(
        self,
        task: Task,
        comment: TaskComment,
        attachment_ids: list[str],
        actor: ResolvedCrmSession,
    ) -> None:
        if not attachment_ids:
            return

        self._task_repository.session.flush()

        attachments = list(
            self._task_repository.session.scalars(
                select(TaskAttachment).where(TaskAttachment.attachment_id.in_(attachment_ids))
            ).all()
        )
        if len(attachments) != len(set(attachment_ids)):
            raise TaskValidationError("Uno o más adjuntos indicados no existen.")

        for attachment in attachments:
            if attachment.task_id != task.task_id:
                raise TaskValidationError("Los adjuntos deben pertenecer a la misma tarea del comentario.")
            if attachment.uploaded_by_crm_user_id != actor.crm_user.crm_user_id and "admin" not in actor.role_keys:
                raise TaskAccessDeniedError("No podés asociar adjuntos subidos por otro usuario.")
            if attachment.task_comment_id is not None:
                raise TaskValidationError("Uno de los adjuntos ya fue asociado a otro comentario.")
            attachment.task_comment_id = comment.task_comment_id

    def _try_register_arrival_from_comment(
        self,
        *,
        actor: ResolvedCrmSession,
        task: Task,
        comment: TaskComment,
        has_multimedia: bool,
    ) -> None:
        if not has_multimedia:
            return
        if not comment.location_id:
            return
        subtask = self._subtask_for_comment(task, comment)
        if subtask is not None and not subtask.requires_arrival_comment:
            return
        if subtask is None and not task.requires_arrival_comment:
            return
        if task.arrival_registered_at is not None or task.arrival_comment_id is not None:
            return

        self._task_repository.session.flush()
        task.arrival_registered_at = datetime.now(UTC)
        task.arrival_comment_id = comment.task_comment_id
        if comment.comment_type == TaskCommentType.GENERAL.value:
            comment.comment_type = TaskCommentType.ARRIVAL_REGISTRATION.value

        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.arrival_registered",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "task_comment_id": comment.task_comment_id,
                    "location_id": comment.location_id,
                },
            )
        )

    def _attachment_ids_have_media(self, task: Task, attachment_ids: list[str], subtask_id: str | None = None) -> bool:
        if not attachment_ids:
            return False

        attachments = list(
            self._task_repository.session.scalars(
                select(TaskAttachment).where(TaskAttachment.attachment_id.in_(attachment_ids))
            ).all()
        )
        if len(attachments) != len(set(attachment_ids)):
            raise TaskValidationError("Uno o más adjuntos indicados no existen.")

        for attachment in attachments:
            if attachment.task_id != task.task_id:
                raise TaskValidationError("Los adjuntos de cierre deben pertenecer a la misma tarea.")
            if subtask_id is not None and attachment.subtask_id != subtask_id:
                raise TaskValidationError("Los adjuntos de cierre deben pertenecer a la misma subtarea.")

        allowed_media_types = {TaskAttachmentType.PHOTO.value, TaskAttachmentType.VIDEO.value}
        return any(attachment.attachment_type in allowed_media_types for attachment in attachments)

    def _task_has_closure_media_evidence(self, task: Task, subtask_id: str | None = None) -> bool:
        closure_comment_ids = {
            comment.task_comment_id
            for comment in task.comments
            if comment.comment_type == TaskCommentType.CLOSURE_EVIDENCE.value
            and (subtask_id is None or comment.subtask_id == subtask_id)
        }
        if not closure_comment_ids:
            return False

        allowed_media_types = {TaskAttachmentType.PHOTO.value, TaskAttachmentType.VIDEO.value}
        return any(
            attachment.attachment_type in allowed_media_types
            for attachment in self._task_repository.session.scalars(
                select(TaskAttachment).where(TaskAttachment.task_id == task.task_id)
            ).all()
            if attachment.task_comment_id in closure_comment_ids
        )

    def _validate_task_close_requirements(self, task: Task, subtask: Subtask, attachment_ids: list[str]) -> None:
        next_subtask = next((item for item in task.subtasks if item.order_index == subtask.order_index + 1), None)
        has_subtask_arrival_rules = any(item.requires_arrival_comment for item in task.subtasks)
        has_subtask_media_rules = any(item.requires_video_evidence for item in task.subtasks)
        requires_arrival = subtask.requires_arrival_comment or (
            next_subtask is None and task.requires_arrival_comment and not has_subtask_arrival_rules
        )
        requires_media = subtask.requires_video_evidence or (
            next_subtask is None and task.requires_video_evidence and not has_subtask_media_rules
        )

        if requires_arrival and task.arrival_registered_at is None:
            raise TaskValidationError(
                "Este pedido requiere registrar llegada antes del cierre final. Agregá un comentario con ubicación y multimedia."
            )

        if requires_media and not self._attachment_ids_have_media(task, attachment_ids, subtask.subtask_id):
            raise TaskValidationError("El cierre de esta subtarea requiere al menos un adjunto multimedia (foto o video) como evidencia.")

    def _subtask_for_comment(self, task: Task, comment: TaskComment) -> Subtask | None:
        if comment.subtask_id is None:
            return None
        return next((subtask for subtask in task.subtasks if subtask.subtask_id == comment.subtask_id), None)

    def _task_has_pending_required_arrival(self, task: Task) -> bool:
        return (task.requires_arrival_comment or any(subtask.requires_arrival_comment for subtask in task.subtasks)) and task.arrival_registered_at is None

    def _task_has_pending_required_closure_media(self, task: Task) -> bool:
        required_subtasks = [subtask for subtask in task.subtasks if subtask.requires_video_evidence]
        if not required_subtasks and task.requires_video_evidence:
            return not self._task_has_closure_media_evidence(task)
        return any(
            not self._task_has_closure_media_evidence(task, subtask.subtask_id)
            for subtask in required_subtasks
        )

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def _build_close_validator_chain(self, base_chain: ActorPermissionValidator) -> ActorPermissionValidator:
        actor_validator = ActorPermissionValidator()
        actor_validator.set_next(StateActionValidator()).set_next(RequiredCommentValidator()).set_next(
            RequiredItemsCompletedValidator(self._item_strategy_registry)
        ).set_next(
            PendingInventoryRequestsResolvedValidator()
        ).set_next(
            NextAssignmentValidator(self._assignment_strategy_registry, self._user_repository)
        ).set_next(
            TransitionIntegrityValidator()
        )
        return actor_validator

    def _ensure_admin_or_executive(self, actor: ResolvedCrmSession) -> None:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("La operación requiere rol administrador o ejecutivo.")

    def _ensure_admin(self, actor: ResolvedCrmSession) -> None:
        if "admin" not in actor.role_keys:
            raise TaskAccessDeniedError("La operación requiere rol administrador.")

    def _ensure_assignment_access(self, actor: ResolvedCrmSession, subtask: Subtask) -> None:
        if self._permission_service is not None and self._permission_service.resolve(
            actor.role_keys,
            actor.crm_user.crm_user_id,
            PERMISSION_TICKET_REASSIGN,
        ):
            return
        raise TaskAccessDeniedError(
            "La operación requiere permiso para reasignar tickets/pedidos."
        )

    def _is_task_pending_executive_approval(self, task: Task) -> bool:
        if task.status != TaskStatus.BLOCKED.value or task.is_finalized:
            return False
        if task.current_assigned_crm_user_id is None:
            return False
        if any(subtask.status != SubtaskStatus.COMPLETED.value for subtask in task.subtasks):
            return False

        approver = self._user_repository.get_by_id(task.current_assigned_crm_user_id)
        if approver is None:
            return False

        approver_role_keys = {
            assignment.role.role_key
            for assignment in approver.assigned_roles
            if assignment.role is not None
        }
        return bool({"ejecutivo", "admin_crm"}.intersection(approver_role_keys))

    def _ensure_read_access(self, actor: ResolvedCrmSession) -> None:
        if not {"admin", "ejecutivo", "deposito", "tecnico"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError()

    def _ensure_subtask_is_operable_by_actor(self, actor: ResolvedCrmSession, subtask: Subtask) -> None:
        self._ensure_read_access(actor)
        if subtask.assigned_crm_user_id != actor.crm_user.crm_user_id:
            raise TaskAccessDeniedError("La subtarea solo puede ser operada por el usuario asignado.")

    def _ensure_task_operable(self, actor: ResolvedCrmSession, task: Task) -> None:
        self._ensure_read_access(actor)
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return

        actor_id = actor.crm_user.crm_user_id
        if task.current_assigned_crm_user_id == actor_id:
            return

        if any(
            subtask.assigned_crm_user_id == actor_id
            and subtask.status in {
                SubtaskStatus.ASSIGNED.value,
                SubtaskStatus.IN_PROGRESS.value,
                SubtaskStatus.REJECTED.value,
                SubtaskStatus.ON_HOLD.value,
            }
            for subtask in task.subtasks
        ):
            return

        raise TaskAccessDeniedError("Solo el operador activo o perfiles ejecutivo/admin pueden comentar en este pedido.")

    def _resolve_mentioned_users(self, mentioned_user_ids: list[str]) -> list[object]:
        normalized_ids: list[str] = []
        seen: set[str] = set()
        for raw_user_id in mentioned_user_ids:
            normalized = raw_user_id.strip() if isinstance(raw_user_id, str) else ""
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            normalized_ids.append(normalized)
        if not normalized_ids:
            return []

        users = self._user_repository.list_active_by_ids(normalized_ids)
        users_by_id = {user.crm_user_id: user for user in users}
        missing_ids = [user_id for user_id in normalized_ids if user_id not in users_by_id]
        if missing_ids:
            raise TaskValidationError("Uno de los usuarios mencionados no existe o no está activo.")
        return [users_by_id[user_id] for user_id in normalized_ids]

    def _log_comment_mention(self, actor: ResolvedCrmSession, task: Task, comment: TaskComment, mentioned_user: object) -> None:
        if self._activity_log_service is None:
            return
        actor_label = actor.crm_user.display_name or actor.crm_user.email or actor.crm_user.crm_user_id
        mentioned_label = (
            getattr(mentioned_user, "display_name", None)
            or getattr(mentioned_user, "email", None)
            or getattr(mentioned_user, "crm_user_id")
        )
        self._activity_log_service.log(
            "task.comment_mention.created",
            actor,
            entity_type="task",
            entity_id=task.task_id,
            entity_label=task.task_title,
            summary=f"{actor_label} mencionó a {mentioned_label} en la tarea {task.task_title}.",
            extra={
                "comment_id": comment.task_comment_id,
                "mentioned_user_id": getattr(mentioned_user, "crm_user_id"),
                "mentioned_user_display_name": mentioned_label,
                "task_id": task.task_id,
                "subtask_id": comment.subtask_id,
            },
        )

    def _validate_default_user(self, crm_user_id: str | None, role_key: str) -> None:
        if crm_user_id is None:
            return
        user = self._user_repository.get_by_id(crm_user_id)
        if user is None:
            raise TaskValidationError("El usuario responsable por defecto no existe.")
        valid_role_keys = {role_key, {"admin": "admin_crm", "deposito": "encargado_deposito", "tecnico": "tecnico_campo"}.get(role_key, role_key)}
        if not any(assignment.role and assignment.role.role_key in valid_role_keys for assignment in user.assigned_roles):
            raise TaskValidationError("El usuario responsable por defecto no posee el rol requerido.")

    def _append_extra_materials(self, task: Task, payload: CreateTaskFromTemplateRequest) -> None:
        if not payload.extra_materials:
            return

        product_ids = [item.product_id for item in payload.extra_materials]
        if len(product_ids) != len(set(product_ids)):
            raise TaskValidationError("No se puede repetir el mismo producto en materiales adicionales.")

        products = {
            product.product_id: product
            for product in self._task_repository.session.scalars(
                select(StockProduct).where(
                    StockProduct.product_id.in_(product_ids),
                    StockProduct.is_active.is_(True),
                    StockProduct.deleted_at.is_(None),
                )
            ).all()
        }

        for item in payload.extra_materials:
            product = products.get(item.product_id)
            if product is None:
                raise TaskValidationError("Uno de los productos indicados no existe o está inactivo.")
            task.extra_materials.append(
                TaskExtraMaterial(
                    product_id=product.product_id,
                    quantity=int(item.quantity),
                )
            )

    def _notify_task_creation_state(self, task: Task) -> None:
        if self._notification_service is None:
            return

        current_subtask = next(
            (
                item
                for item in sorted(task.subtasks, key=lambda candidate: candidate.order_index)
                if item.status in {SubtaskStatus.PENDING_ASSIGNMENT.value, SubtaskStatus.ASSIGNED.value, SubtaskStatus.IN_PROGRESS.value}
            ),
            None,
        )
        if current_subtask is None:
            return

        task_label = task.task_id[:8].upper()
        try:
            if current_subtask.assigned_crm_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=current_subtask.assigned_crm_user_id,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title=f"Pedido #{task_label} asignado a vos",
                    body=f"Se te asignó el pedido '{task.task_title}'.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
                ejecutivo_ids = self._notification_service.resolve_users_with_role_key("ejecutivo")
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=ejecutivo_ids,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title=f"Pedido #{task_label} asignado",
                    body=f"El pedido '{task.task_title}' fue asignado para ejecución.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
                return

            if current_subtask.status == SubtaskStatus.PENDING_ASSIGNMENT.value and current_subtask.responsible_role_key:
                role_user_ids = self._notification_service.resolve_users_with_role_key(current_subtask.responsible_role_key)
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=role_user_ids,
                    notification_type=NotificationType.TASK_UNASSIGNED_IN_ROLE,
                    title=f"Pedido #{task_label} sin asignar",
                    body="Hay una subtarea pendiente de asignación para tu rol.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
        except Exception:
            _logger.exception("Error sending task creation notifications for task %s", task.task_id)

    def _notify_unlocked_subtask_state(self, task: Task, *, closed_subtask_id: str) -> None:
        if self._notification_service is None:
            return

        next_subtask = next(
            (
                item
                for item in sorted(task.subtasks, key=lambda candidate: candidate.order_index)
                if item.subtask_id != closed_subtask_id
                and item.status in {SubtaskStatus.PENDING_ASSIGNMENT.value, SubtaskStatus.ASSIGNED.value, SubtaskStatus.IN_PROGRESS.value}
            ),
            None,
        )
        if next_subtask is None:
            return

        task_label = task.task_id[:8].upper()
        try:
            if next_subtask.assigned_crm_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=next_subtask.assigned_crm_user_id,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title=f"Pedido #{task_label} asignado a vos",
                    body=f"Se te asignó el pedido '{task.task_title}'.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
                ejecutivo_ids = self._notification_service.resolve_users_with_role_key("ejecutivo")
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=ejecutivo_ids,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title=f"Pedido #{task_label} asignado",
                    body=f"El pedido '{task.task_title}' fue asignado para ejecución.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
                return

            if next_subtask.status == SubtaskStatus.PENDING_ASSIGNMENT.value and next_subtask.responsible_role_key:
                role_user_ids = self._notification_service.resolve_users_with_role_key(next_subtask.responsible_role_key)
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=role_user_ids,
                    notification_type=NotificationType.TASK_UNASSIGNED_IN_ROLE,
                    title=f"Pedido #{task_label} sin asignar",
                    body="Hay una subtarea pendiente de asignación para tu rol.",
                    entity_type=NotificationEntityType.TASK,
                    entity_id=task.task_id,
                )
        except Exception:
            _logger.exception("Error sending unlocked subtask notifications for task %s", task.task_id)
