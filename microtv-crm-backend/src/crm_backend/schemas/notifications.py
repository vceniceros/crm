"""Pydantic schemas for the notification module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    recipient_crm_user_id: str
    notification_type: str
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None
    metadata_json: dict | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
