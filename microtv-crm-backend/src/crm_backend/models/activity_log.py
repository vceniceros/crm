"""Activity log models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_backend.db.base import Base


class ActivityLog(Base):
    """Live activity log entry."""

    __tablename__ = "activity_log"

    activity_log_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    actor_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_code: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, server_default="{}")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ActivityLogArchive(Base):
    """Archived activity log entry."""

    __tablename__ = "activity_log_archive"

    activity_log_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    actor_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_code: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, server_default="{}")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
