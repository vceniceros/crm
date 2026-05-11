"""Notification domain model for in-app operational alerts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class NotificationType(StrEnum):
    """Supported in-app notification event types."""

    # Ticket events
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_REASSIGNED = "ticket_reassigned"
    TICKET_REOPENED = "ticket_reopened"
    TICKET_PENDING_APPROVAL = "ticket_pending_approval"
    TICKET_APPROVED = "ticket_approved"
    TICKET_REJECTED = "ticket_rejected"
    TICKET_RETURNED_TO_TECHNICIAN = "ticket_returned_to_technician"

    # Task / subtask events
    TASK_ASSIGNED = "task_assigned"
    TASK_SUBTASK_ASSIGNED = "task_subtask_assigned"
    TASK_SUBTASK_REASSIGNED = "task_subtask_reassigned"
    TASK_PRE_FORM_COMPLETED = "task_pre_form_completed"
    TASK_SATISFACTION_SUBMITTED = "task_satisfaction_submitted"
    TASK_UNASSIGNED_IN_ROLE = "task_unassigned_in_role"
    TASK_PENDING_APPROVAL = "task_pending_approval"
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"

    # Ticket feedback and assignment state events
    TICKET_SATISFACTION_SUBMITTED = "ticket_satisfaction_submitted"
    TICKET_UNASSIGNED_IN_ROLE = "ticket_unassigned_in_role"

    # Stock alerts
    STOCK_LOW = "stock_low"
    STOCK_OUT = "stock_out"

    # Deposit / inventory request events
    DEPOSIT_PENDING_DISPATCH = "deposit_pending_dispatch"
    DEPOSIT_PRODUCTS_INSTALLED = "deposit_products_installed"
    DEPOSIT_REQUEST_CREATED = "deposit_request_created"
    DEPOSIT_REQUEST_APPROVED = "deposit_request_approved"
    DEPOSIT_REQUEST_REJECTED = "deposit_request_rejected"
    DEPOSIT_REQUEST_DISPATCHED = "deposit_request_dispatched"
    DEPOSIT_REQUEST_RECEIPT_PENDING = "deposit_request_receipt_pending"
    DEPOSIT_REQUEST_RECEIVED = "deposit_request_received"


class NotificationEntityType(StrEnum):
    """Entity types that a notification can reference."""

    TICKET = "ticket"
    TASK = "task"
    STOCK_PRODUCT = "stock_product"
    DEPOSIT_REQUEST = "deposit_request"


class Notification(Base):
    """Persisted in-app notification record."""

    __tablename__ = "crm_notifications"

    notification_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    recipient_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
