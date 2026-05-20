"""Asset link models for tickets and tasks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.asset import Asset
    from crm_backend.models.crm_user import CrmUser
    from crm_backend.models.task_execution import Task
    from crm_backend.models.ticket import Ticket


class TicketAsset(Base):
    """M:M link between tickets and assets."""

    __tablename__ = "ticket_assets"
    __table_args__ = (UniqueConstraint("ticket_id", "asset_id", name="uq_ticket_assets_ticket_asset"),)

    ticket_asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("assets.asset_id"), index=True)
    linked_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="asset_links", lazy="joined")
    asset: Mapped["Asset"] = relationship("Asset", lazy="joined")
    linked_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[linked_by_crm_user_id], lazy="joined")


class TaskAsset(Base):
    """M:M link between tasks and assets."""

    __tablename__ = "task_assets"
    __table_args__ = (UniqueConstraint("task_id", "asset_id", name="uq_task_assets_task_asset"),)

    task_asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("assets.asset_id"), index=True)
    linked_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["Task"] = relationship("Task", lazy="joined")
    asset: Mapped["Asset"] = relationship("Asset", lazy="joined")
    linked_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[linked_by_crm_user_id], lazy="joined")
