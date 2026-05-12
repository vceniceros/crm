"""Activity log endpoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from crm_backend.api.dependencies import (
    get_activity_log_service,
    get_authenticated_crm_session,
    get_crm_user_repository,
)
from crm_backend.repositories.activity_log_repository import ActivityLogFilters as RepoActivityLogFilters
from crm_backend.schemas import ErrorResponse
from crm_backend.schemas.activity_log import ActivityLogEntryResponse, ActivityLogPageResponse
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.repositories import CrmUserRepository


router = APIRouter(prefix="/activity-log", tags=["activity-log"])


@router.get("", response_model=ActivityLogPageResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_activity_log(
    user_id: str | None = Query(default=None),
    event_code: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    service: ActivityLogService = Depends(get_activity_log_service),
    user_repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> ActivityLogPageResponse:
    filters = RepoActivityLogFilters(
        actor_crm_user_id=user_id,
        event_code_prefix=event_code,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    rows, total = service.list_for_admin(actor, filters)

    user_ids = sorted({row.actor_crm_user_id for row in rows if row.actor_crm_user_id})
    user_name_map: dict[str, str] = {}
    for crm_user_id in user_ids:
        user = user_repository.get_by_id(crm_user_id)
        if user is not None:
            user_name_map[crm_user_id] = user.display_name or user.email or crm_user_id

    show_ip = "admin" in actor.role_keys
    items = [
        ActivityLogEntryResponse(
            activity_log_id=row.activity_log_id,
            actor_crm_user_id=row.actor_crm_user_id,
            actor_display_name=user_name_map.get(row.actor_crm_user_id or "") if row.actor_crm_user_id else "Sistema",
            event_code=row.event_code,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            entity_label=row.entity_label,
            summary=row.summary,
            payload_json=row.payload_json or {},
            ip_address=row.ip_address if show_ip else None,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return ActivityLogPageResponse(items=items, total=total, page=page, per_page=per_page)
