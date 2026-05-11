"""Task pre-form service: secure public intake form before task execution."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm import Session

from crm_backend.core.exceptions import TaskAccessDeniedError, TaskConflictError, TaskPreFormNotFoundError, TaskValidationError
from crm_backend.models import SubtaskStatus, Task, TaskPreFormFieldValue, TaskPreFormInstance, TaskPreFormResponse, TaskStatus

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession

_DEFAULT_EXPIRY_HOURS = 72


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


class TaskPreFormService:
    """Manage secure generation and submission of task pre-forms."""

    def __init__(self, session: Session, expiry_hours: int = _DEFAULT_EXPIRY_HOURS) -> None:
        self._session = session
        self._expiry_hours = expiry_hours

    def generate_or_regenerate_link(self, actor: "ResolvedCrmSession", task: Task) -> tuple[TaskPreFormInstance, str]:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden generar links de formulario previo.")

        template_pre_form = task.template.pre_form
        if template_pre_form is None:
            raise TaskValidationError("El template de este pedido no tiene formulario previo configurado.")

        existing = (
            self._session.query(TaskPreFormInstance)
            .filter_by(task_id=task.task_id)
            .order_by(TaskPreFormInstance.created_at.desc())
            .first()
        )
        if existing is not None and existing.submitted_at is not None:
            raise TaskConflictError("El formulario previo ya fue completado y no puede regenerarse.")

        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(hours=self._expiry_hours)

        if existing is None:
            instance = TaskPreFormInstance(
                instance_id=str(uuid4()),
                task_id=task.task_id,
                template_pre_form_id=template_pre_form.form_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            self._session.add(instance)
        else:
            existing.token_hash = token_hash
            existing.expires_at = expires_at
            existing.revoked_at = None
            instance = existing

        self._session.commit()
        self._session.refresh(instance)
        return instance, raw_token

    def get_status(self, actor: "ResolvedCrmSession", task: Task) -> TaskPreFormInstance | None:
        if not {"admin", "ejecutivo", "tecnico", "deposito"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("No tenés permisos para consultar estado de formulario previo.")

        return (
            self._session.query(TaskPreFormInstance)
            .filter_by(task_id=task.task_id)
            .order_by(TaskPreFormInstance.created_at.desc())
            .first()
        )

    def get_public_form_info(self, raw_token: str) -> TaskPreFormInstance:
        return self._resolve_token(raw_token)

    def submit_response(
        self,
        raw_token: str,
        values: list[dict[str, str | None]],
        submitter_ip: str | None,
    ) -> TaskPreFormResponse:
        instance = self._resolve_token(raw_token)
        if instance.template_pre_form is None:
            raise TaskValidationError("El formulario previo no tiene definición válida.")

        now = datetime.now(UTC)
        instance.submitted_at = now
        self._session.flush()

        field_by_id = {field.field_id: field for field in instance.template_pre_form.fields}
        response = TaskPreFormResponse(
            response_id=str(uuid4()),
            instance_id=instance.instance_id,
            task_id=instance.task_id,
            submitter_ip_hash=_hash_ip(submitter_ip) if submitter_ip else None,
        )
        self._session.add(response)
        self._session.flush()

        for item in values:
            field_id = (item.get("field_id") or "").strip()
            if not field_id:
                continue
            field = field_by_id.get(field_id)
            if field is None:
                raise TaskValidationError("Uno de los campos enviados no pertenece al formulario previo.")

            text_value = (item.get("text_value") or "").strip() or None
            if field.is_required and not text_value:
                raise TaskValidationError(f"El campo obligatorio '{field.label}' no fue completado.")

            response.field_values.append(
                TaskPreFormFieldValue(
                    value_id=str(uuid4()),
                    field_id=field.field_id,
                    text_value=text_value,
                )
            )

        self._mark_pre_form_subtask_completed(instance.task, now)
        self._session.commit()
        self._session.refresh(response)
        return response

    def _resolve_token(self, raw_token: str) -> TaskPreFormInstance:
        if not raw_token or len(raw_token) > 200:
            raise TaskPreFormNotFoundError()

        token_hash = _hash_token(raw_token)
        instance = self._session.query(TaskPreFormInstance).filter_by(token_hash=token_hash).first()
        if instance is None or not instance.is_usable:
            raise TaskPreFormNotFoundError()
        return instance

    def _mark_pre_form_subtask_completed(self, task: Task, completed_at: datetime) -> None:
        pre_form_subtask = next((subtask for subtask in task.subtasks if subtask.subtask_type == "pre_form"), None)
        if pre_form_subtask is None:
            return

        pre_form_subtask.status = SubtaskStatus.COMPLETED.value
        pre_form_subtask.is_completed = True
        pre_form_subtask.completed_at = completed_at
        pre_form_subtask.completion_notes = "Formulario previo completado por el cliente."

        next_subtask = next((subtask for subtask in task.subtasks if subtask.order_index == pre_form_subtask.order_index + 1), None)
        if next_subtask is not None and next_subtask.status == SubtaskStatus.LOCKED.value:
            next_subtask.assigned_crm_user_id = next_subtask.default_responsible_crm_user_id
            next_subtask.status = (
                SubtaskStatus.ASSIGNED.value
                if next_subtask.assigned_crm_user_id is not None
                else SubtaskStatus.PENDING_ASSIGNMENT.value
            )
            task.current_assigned_crm_user_id = next_subtask.assigned_crm_user_id
            task.status = TaskStatus.IN_PROGRESS.value
