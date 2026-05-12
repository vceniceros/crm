"""Repository for activity log entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crm_backend.models import ActivityLog


@dataclass(slots=True)
class ActivityLogFilters:
    actor_crm_user_id: str | None = None
    event_code_prefix: str | None = None
    entity_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    per_page: int = 50


class ActivityLogRepository:
    """Persistence helper for activity log entries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self,
        *,
        event_code: str,
        actor_id: str | None,
        entity_type: str | None,
        entity_id: str | None,
        entity_label: str | None,
        summary: str | None,
        payload_json: dict[str, object],
        ip_address: str | None = None,
    ) -> ActivityLog:
        row = ActivityLog(
            actor_crm_user_id=actor_id,
            event_code=event_code,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            summary=summary,
            payload_json=payload_json,
            ip_address=ip_address,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_paginated(self, filters: ActivityLogFilters) -> tuple[list[ActivityLog], int]:
        statement = select(ActivityLog)
        count_statement = select(func.count()).select_from(ActivityLog)

        if filters.actor_crm_user_id:
            statement = statement.where(ActivityLog.actor_crm_user_id == filters.actor_crm_user_id)
            count_statement = count_statement.where(ActivityLog.actor_crm_user_id == filters.actor_crm_user_id)
        if filters.event_code_prefix:
            prefix = f"{filters.event_code_prefix}%"
            statement = statement.where(ActivityLog.event_code.ilike(prefix))
            count_statement = count_statement.where(ActivityLog.event_code.ilike(prefix))
        if filters.entity_type:
            statement = statement.where(ActivityLog.entity_type == filters.entity_type)
            count_statement = count_statement.where(ActivityLog.entity_type == filters.entity_type)
        if filters.date_from:
            statement = statement.where(ActivityLog.created_at >= filters.date_from)
            count_statement = count_statement.where(ActivityLog.created_at >= filters.date_from)
        if filters.date_to:
            statement = statement.where(ActivityLog.created_at <= filters.date_to)
            count_statement = count_statement.where(ActivityLog.created_at <= filters.date_to)

        total = int(self._session.scalar(count_statement) or 0)
        page = max(filters.page, 1)
        per_page = min(max(filters.per_page, 1), 200)
        offset = (page - 1) * per_page

        rows = list(
            self._session.scalars(
                statement.order_by(ActivityLog.created_at.desc()).offset(offset).limit(per_page)
            ).all()
        )
        return rows, total
