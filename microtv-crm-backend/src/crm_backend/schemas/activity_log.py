"""Schemas for activity log API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ActivityLogFilters(BaseModel):
    user_id: str | None = None
    event_code: str | None = None
    entity_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)


class ActivityLogEntryResponse(BaseModel):
    activity_log_id: str
    actor_crm_user_id: str | None
    actor_display_name: str | None
    event_code: str
    entity_type: str | None
    entity_id: str | None
    entity_label: str | None
    summary: str | None
    payload_json: dict[str, object]
    ip_address: str | None
    created_at: datetime


class ActivityLogPageResponse(BaseModel):
    items: list[ActivityLogEntryResponse]
    total: int
    page: int
    per_page: int
