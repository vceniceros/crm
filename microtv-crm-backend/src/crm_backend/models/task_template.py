"""Task template domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.task_execution import TaskTemplatePreForm


class TemplateItemType(StrEnum):
    """Supported task template item types."""

    CHECKBOX = "checkbox"
    TEXT = "text"


class NextAssignmentPolicy(StrEnum):
    """Supported assignment policies for the next subtask."""

    ROLE_QUEUE_AUTO = "role_queue_auto"
    DEFAULT_USER_AUTO = "default_user_auto"
    MANUAL_REQUIRED = "manual_required"


class SubtaskType(StrEnum):
    """Supported task subtask types."""

    STANDARD = "standard"
    PRE_FORM = "pre_form"


class TaskTemplate(Base):
    """Reusable operational task template."""

    __tablename__ = "task_templates"

    template_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    template_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    requires_arrival_comment: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    requires_video_evidence: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    requires_pre_form: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subtasks: Mapped[list[TaskTemplateSubtask]] = relationship(
        "TaskTemplateSubtask",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TaskTemplateSubtask.order_index",
        lazy="selectin",
    )
    required_materials: Mapped[list[TemplateMaterial]] = relationship(
        "TemplateMaterial",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateMaterial.created_at",
        lazy="selectin",
    )
    pre_form: Mapped["TaskTemplatePreForm | None"] = relationship(
        "TaskTemplatePreForm",
        back_populates="template",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class TaskTemplateSubtask(Base):
    """Ordered subtask definition inside a task template."""

    __tablename__ = "template_subtasks"

    template_subtask_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    template_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("task_templates.template_id"), index=True)
    subtask_title: Mapped[str] = mapped_column(String(255))
    subtask_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)
    responsible_role_key: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    default_responsible_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id"),
        nullable=True,
    )
    close_comment_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    next_assignment_policy: Mapped[str] = mapped_column(String(50), default=NextAssignmentPolicy.ROLE_QUEUE_AUTO.value)
    subtask_type: Mapped[str] = mapped_column(String(50), default=SubtaskType.STANDARD.value, server_default=SubtaskType.STANDARD.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped[TaskTemplate] = relationship("TaskTemplate", back_populates="subtasks")
    items: Mapped[list[TaskTemplateItem]] = relationship(
        "TaskTemplateItem",
        back_populates="template_subtask",
        cascade="all, delete-orphan",
        order_by="TaskTemplateItem.item_order",
        lazy="selectin",
    )

    @property
    def task_template_subtask_id(self) -> str:
        return self.template_subtask_id


class TaskTemplateItem(Base):
    """Template checklist item definition."""

    __tablename__ = "template_subtask_checklist_items"

    template_checklist_item_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    template_subtask_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("template_subtasks.template_subtask_id"),
        index=True,
    )
    item_label: Mapped[str] = mapped_column(String(500))
    item_order: Mapped[int] = mapped_column(Integer)
    item_type: Mapped[str] = mapped_column(String(50), default=TemplateItemType.CHECKBOX.value)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template_subtask: Mapped[TaskTemplateSubtask] = relationship("TaskTemplateSubtask", back_populates="items")

    @property
    def task_template_item_id(self) -> str:
        return self.template_checklist_item_id