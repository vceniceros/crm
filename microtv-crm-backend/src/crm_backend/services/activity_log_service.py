"""Activity log service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from crm_backend.core.exceptions import ApplicationError
from crm_backend.repositories.activity_log_repository import ActivityLogFilters, ActivityLogRepository

if TYPE_CHECKING:
    from crm_backend.services.auth_service import ResolvedCrmSession


class ActivityLogService:
    """Application service for writing and reading activity logs."""

    def __init__(self, repository: ActivityLogRepository) -> None:
        self._repository = repository

    def log(
        self,
        event_code: str,
        actor: ResolvedCrmSession | None,
        *,
        actor_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        entity_label: str | None = None,
        summary: str | None = None,
        extra: dict[str, object] | None = None,
        ip_address: str | None = None,
    ) -> None:
        resolved_actor_id = actor_id or (actor.crm_user.crm_user_id if actor is not None else None)
        self._repository.insert(
            event_code=event_code,
            actor_id=resolved_actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            summary=summary,
            payload_json=extra or {},
            ip_address=ip_address,
        )

    def list_for_admin(self, actor: ResolvedCrmSession, filters: ActivityLogFilters):
        if "admin" not in actor.role_keys and "ejecutivo" not in actor.role_keys:
            raise ApplicationError("activity_log_access_denied", "No tiene permisos para consultar el registro de actividad.", 403)

        rows, total = self._repository.list_paginated(filters)
        if "admin" in actor.role_keys:
            return rows, total

        filtered_rows = [row for row in rows if not row.event_code.startswith("settings.permissions")]
        return filtered_rows, total
