"""Task satisfaction form service: secure one-use survey links for completed tasks."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm import Session

from crm_backend.core.exceptions import SatisfactionFormConflictError, SatisfactionFormNotFoundError, TaskAccessDeniedError, TaskValidationError
from crm_backend.models import Task, TaskSatisfactionForm, TaskSatisfactionResponse, TaskStatus

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession

_DEFAULT_EXPIRY_HOURS = 72


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


class TaskSatisfactionFormService:
    """Manage task satisfaction form generation, status and public submissions."""

    def __init__(self, session: Session, expiry_hours: int = _DEFAULT_EXPIRY_HOURS) -> None:
        self._session = session
        self._expiry_hours = expiry_hours

    def generate_form(self, actor: "ResolvedCrmSession", task: Task) -> tuple[TaskSatisfactionForm, str]:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden generar encuestas de satisfacción.")
        if task.status != TaskStatus.COMPLETED.value:
            raise TaskAccessDeniedError("Solo se puede generar encuesta cuando el pedido está completado.")

        existing = (
            self._session.query(TaskSatisfactionForm)
            .filter_by(task_id=task.task_id)
            .filter(TaskSatisfactionForm.revoked_at.is_(None))
            .filter(TaskSatisfactionForm.expires_at > datetime.now(UTC))
            .first()
        )
        if existing is not None:
            raise SatisfactionFormConflictError(
                "Ya existe un formulario activo para este pedido. Revocalo antes de generar uno nuevo."
            )

        raw_token = secrets.token_urlsafe(48)
        form = TaskSatisfactionForm(
            form_id=str(uuid4()),
            task_id=task.task_id,
            token_hash=_hash_token(raw_token),
            created_by_user_id=actor.crm_user.crm_user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=self._expiry_hours),
        )
        self._session.add(form)
        self._session.commit()
        self._session.refresh(form)
        return form, raw_token

    def get_form_status(self, actor: "ResolvedCrmSession", task: Task) -> TaskSatisfactionForm | None:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden consultar estado de encuesta.")

        return (
            self._session.query(TaskSatisfactionForm)
            .filter_by(task_id=task.task_id)
            .order_by(TaskSatisfactionForm.created_at.desc())
            .first()
        )

    def revoke_form(self, actor: "ResolvedCrmSession", task: Task) -> TaskSatisfactionForm:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden revocar encuestas.")

        form = (
            self._session.query(TaskSatisfactionForm)
            .filter_by(task_id=task.task_id)
            .filter(TaskSatisfactionForm.revoked_at.is_(None))
            .order_by(TaskSatisfactionForm.created_at.desc())
            .first()
        )
        if form is None:
            raise SatisfactionFormNotFoundError()
        if form.used_at is not None:
            raise SatisfactionFormConflictError("El formulario ya fue respondido y no puede revocarse.")

        form.revoked_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(form)
        return form

    def get_response_for_task(self, actor: "ResolvedCrmSession", task: Task) -> TaskSatisfactionResponse | None:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise TaskAccessDeniedError("Solo admin o ejecutivo pueden consultar respuestas de satisfacción.")

        form = (
            self._session.query(TaskSatisfactionForm)
            .filter_by(task_id=task.task_id)
            .filter(TaskSatisfactionForm.used_at.isnot(None))
            .order_by(TaskSatisfactionForm.created_at.desc())
            .first()
        )
        if form is None or form.response is None:
            return None
        return form.response

    def get_public_form_info(self, raw_token: str) -> TaskSatisfactionForm:
        return self._resolve_token(raw_token)

    def submit_response(
        self,
        raw_token: str,
        *,
        rating: float,
        customer_name: str,
        customer_company: str,
        comment: str | None,
        submitter_ip: str | None,
        submitter_user_agent: str | None,
    ) -> TaskSatisfactionResponse:
        form = self._resolve_token(raw_token)
        normalized_rating = round(rating * 2) / 2
        if normalized_rating < 0.5 or normalized_rating > 5.0:
            raise TaskValidationError("La puntuación debe estar entre 0.5 y 5.0 estrellas.")

        customer_name = self._normalize_customer_field(customer_name, "nombre")
        customer_company = self._normalize_customer_field(customer_company, "empresa")

        form.used_at = datetime.now(UTC)
        self._session.flush()

        response = TaskSatisfactionResponse(
            response_id=str(uuid4()),
            form_id=form.form_id,
            task_id=form.task_id,
            customer_name=customer_name,
            customer_company=customer_company,
            rating=normalized_rating,
            comment=(comment or "").strip() or None,
            submitter_ip_hash=_hash_ip(submitter_ip) if submitter_ip else None,
            submitter_user_agent=(submitter_user_agent or "")[:500] or None,
        )
        self._session.add(response)
        self._session.commit()
        self._session.refresh(response)
        return response

    def _resolve_token(self, raw_token: str) -> TaskSatisfactionForm:
        if not raw_token or len(raw_token) > 200:
            raise SatisfactionFormNotFoundError()

        token_hash = _hash_token(raw_token)
        form = self._session.query(TaskSatisfactionForm).filter_by(token_hash=token_hash).first()
        if form is None or not form.is_usable:
            raise SatisfactionFormNotFoundError()
        return form

    def _normalize_customer_field(self, value: str, field_label: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise TaskValidationError(f"Debes indicar {field_label} del cliente para responder la encuesta.")
        if len(normalized) > 255:
            raise TaskValidationError(f"El campo {field_label} supera el máximo permitido de 255 caracteres.")
        return normalized
