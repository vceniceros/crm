"""Configurable CRM settings domain models."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.crm_role import CrmRole


class CrmCategory(Base):
    """Configurable category used across CRM entities (tickets, tasks)."""

    __tablename__ = "crm_categories"

    category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), index=True)
    category_type: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Default role assigned when creating a ticket/task with this category
    default_role_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("crm_roles.crm_role_id"), nullable=True, index=True
    )

    # Automatic scheduling settings (only for categories that allow it)
    allows_scheduling: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Period type: 'daily', 'weekly', 'biweekly', 'monthly', 'custom'
    schedule_period_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    schedule_interval_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_weekdays_json: Mapped[list[int]] = mapped_column(JSON, default=list)
    schedule_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    schedule_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    default_role: Mapped["CrmRole | None"] = relationship("CrmRole", foreign_keys=[default_role_id], lazy="joined")


class CrmPriority(Base):
    """Configurable priorities that coexist with legacy enum values."""

    __tablename__ = "crm_priorities"

    priority_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrmStatus(Base):
    """Configurable statuses by entity type (ticket/task/deposit)."""

    __tablename__ = "crm_statuses"
    __table_args__ = (UniqueConstraint("code", "entity_type", name="uq_crm_status_code_entity"),)

    status_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SlaRule(Base):
    """Service-level settings by entity type and priority code."""

    __tablename__ = "crm_sla_rules"

    sla_rule_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    priority_code: Mapped[str] = mapped_column(String(40), index=True)
    response_time_minutes: Mapped[int] = mapped_column(Integer)
    resolution_time_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationRule(Base):
    """Configurable notification behaviors without duplicating dispatch engine."""

    __tablename__ = "crm_notification_rules"

    notification_rule_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    event_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(180))
    notify_assigned: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    notify_roles_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
