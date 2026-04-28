"""Task execution domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.crm_user import CrmUser
    from crm_backend.models.material_flow import InventoryDispatch, InventoryRequest, TaskRequiredMaterial
    from crm_backend.models.task_reference import Client, Location
    from crm_backend.models.task_template import TaskTemplate


class TaskStatus(StrEnum):
    """Task aggregate lifecycle states."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMPLETED = "COMPLETED"


class SubtaskStatus(StrEnum):
    """Subtask execution states."""

    LOCKED = "locked"
    PENDING_ASSIGNMENT = "pending_assignment"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"


class TaskCommentType(StrEnum):
    """Supported task comment types."""

    GENERAL = "general"
    TRANSITION = "transition"
    PROGRESS = "progress"


class TaskAttachmentType(StrEnum):
    """Supported persisted attachment types."""

    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class TransitionAction(StrEnum):
    """Supported subtask actions."""

    CLAIM_SUBTASK = "claim_subtask"
    ASSIGN_SUBTASK = "assign_subtask"
    START_SUBTASK = "start_subtask"
    CLOSE_SUBTASK = "close_subtask"
    REJECT_SUBTASK = "reject_subtask"
    PUT_ON_HOLD = "put_on_hold"


class Task(Base):
    """Task aggregate root instantiated from a template."""

    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("clients.client_id"), index=True)
    location_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("locations.location_id"), nullable=True, index=True)
    template_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("task_templates.template_id"), index=True)
    task_title: Mapped[str] = mapped_column(String(255), index=True)
    task_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(50), default="MEDIA", server_default="MEDIA")
    status: Mapped[str] = mapped_column(String(50), default=TaskStatus.PENDING.value, index=True)
    current_assigned_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id"),
        nullable=True,
        index=True,
    )
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    finalized_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped["Client"] = relationship("Client", lazy="joined")
    template: Mapped["TaskTemplate"] = relationship("TaskTemplate", lazy="joined")
    location: Mapped["Location | None"] = relationship("Location", lazy="selectin")
    current_assigned_user: Mapped["CrmUser | None"] = relationship(
        "CrmUser",
        foreign_keys=[current_assigned_crm_user_id],
        lazy="joined",
    )
    finalized_by_user: Mapped["CrmUser | None"] = relationship(
        "CrmUser",
        primaryjoin="foreign(Task.finalized_by_crm_user_id) == CrmUser.crm_user_id",
        foreign_keys=[finalized_by_crm_user_id],
        lazy="joined",
    )

    subtasks: Mapped[list[Subtask]] = relationship(
        "Subtask",
        back_populates="task",
        foreign_keys="Subtask.task_id",
        cascade="all, delete-orphan",
        order_by="Subtask.order_index",
        lazy="selectin",
    )
    comments: Mapped[list[TaskComment]] = relationship(
        "TaskComment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskComment.created_at",
        lazy="selectin",
    )
    audit_events: Mapped[list[TaskAuditEvent]] = relationship(
        "TaskAuditEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskAuditEvent.created_at",
        lazy="selectin",
    )
    required_materials: Mapped[list[TaskRequiredMaterial]] = relationship(
        "TaskRequiredMaterial",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskRequiredMaterial.created_at",
        lazy="selectin",
    )
    inventory_requests: Mapped[list[InventoryRequest]] = relationship(
        "InventoryRequest",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="InventoryRequest.requested_at.desc()",
        lazy="selectin",
    )
    dispatches: Mapped[list[InventoryDispatch]] = relationship(
        "InventoryDispatch",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="InventoryDispatch.created_at.desc()",
        lazy="selectin",
    )

    @property
    def current_subtask_id(self) -> str | None:
        current_subtask = next(
            (
                item
                for item in sorted(self.subtasks, key=lambda candidate: candidate.order_index)
                if item.status in {
                    SubtaskStatus.PENDING_ASSIGNMENT.value,
                    SubtaskStatus.ASSIGNED.value,
                    SubtaskStatus.IN_PROGRESS.value,
                    SubtaskStatus.REJECTED.value,
                    SubtaskStatus.ON_HOLD.value,
                }
            ),
            None,
        )
        return current_subtask.subtask_id if current_subtask is not None else None

    @property
    def client_name(self) -> str:
        return self.client.business_name

    @property
    def template_name(self) -> str:
        return self.template.template_name

    @property
    def current_assigned_user_display_name(self) -> str | None:
        return _user_display_label(self.current_assigned_user)

    @property
    def finalized_by_display_name(self) -> str | None:
        return _user_display_label(self.finalized_by_user)


class Subtask(Base):
    """Executable subtask instance."""

    __tablename__ = "subtasks"

    subtask_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    parent_subtask_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), nullable=True)
    template_subtask_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("template_subtasks.template_subtask_id"),
        index=True,
    )
    subtask_title: Mapped[str] = mapped_column(String(255))
    subtask_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column()
    current_assigned_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id"),
        nullable=True,
        index=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", index=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_role_key: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    default_responsible_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    close_comment_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    next_assignment_policy: Mapped[str] = mapped_column(String(50), default="role_queue_auto", server_default="role_queue_auto")
    status: Mapped[str] = mapped_column(String(50), default=SubtaskStatus.LOCKED.value, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task: Mapped[Task] = relationship("Task", back_populates="subtasks", foreign_keys=[task_id])
    assigned_user: Mapped["CrmUser | None"] = relationship(
        "CrmUser",
        foreign_keys=[current_assigned_crm_user_id],
        lazy="joined",
    )
    default_assigned_user: Mapped["CrmUser | None"] = relationship(
        "CrmUser",
        foreign_keys=[default_responsible_crm_user_id],
        lazy="joined",
    )
    closed_by_user: Mapped["CrmUser | None"] = relationship(
        "CrmUser",
        foreign_keys=[closed_by_crm_user_id],
        lazy="joined",
    )
    items: Mapped[list[SubtaskItemValue]] = relationship(
        "SubtaskItemValue",
        back_populates="subtask",
        cascade="all, delete-orphan",
        order_by="SubtaskItemValue.item_order",
        lazy="selectin",
    )
    assignments: Mapped[list[SubtaskAssignment]] = relationship(
        "SubtaskAssignment",
        back_populates="subtask",
        cascade="all, delete-orphan",
        order_by="SubtaskAssignment.assigned_at",
        lazy="selectin",
    )
    transitions: Mapped[list[SubtaskTransition]] = relationship(
        "SubtaskTransition",
        back_populates="subtask",
        cascade="all, delete-orphan",
        order_by="SubtaskTransition.created_at",
        lazy="selectin",
    )

    @property
    def assigned_crm_user_id(self) -> str | None:
        return self.current_assigned_crm_user_id

    @assigned_crm_user_id.setter
    def assigned_crm_user_id(self, value: str | None) -> None:
        self.current_assigned_crm_user_id = value

    @property
    def assigned_user_display_name(self) -> str | None:
        return _user_display_label(self.assigned_user)

    @property
    def default_assigned_user_display_name(self) -> str | None:
        return _user_display_label(self.default_assigned_user)

    @property
    def closed_by_display_name(self) -> str | None:
        return _user_display_label(self.closed_by_user)


class SubtaskItemValue(Base):
    """Instantiated subtask item with its current value."""

    __tablename__ = "subtask_checklist_items"

    checklist_item_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    subtask_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), index=True)
    template_checklist_item_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("template_subtask_checklist_items.template_checklist_item_id"),
        nullable=True,
        index=True,
    )
    item_label: Mapped[str] = mapped_column(String(500))
    item_order: Mapped[int] = mapped_column()
    item_type: Mapped[str] = mapped_column(String(50), default="checkbox", server_default="checkbox")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subtask: Mapped[Subtask] = relationship("Subtask", back_populates="items")

    progress: Mapped[SubtaskChecklistProgress | None] = relationship(
        "SubtaskChecklistProgress",
        back_populates="item",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    @property
    def subtask_item_value_id(self) -> str:
        return self.checklist_item_id

    @property
    def template_item_id(self) -> str | None:
        return self.template_checklist_item_id

    @property
    def checkbox_value(self) -> bool:
        return bool(self.progress.is_checked) if self.progress is not None else False

    @checkbox_value.setter
    def checkbox_value(self, value: bool) -> None:
        self._ensure_progress().is_checked = value

    @property
    def text_value(self) -> str | None:
        return self.progress.text_value if self.progress is not None else None

    @text_value.setter
    def text_value(self, value: str | None) -> None:
        self._ensure_progress().text_value = value

    @property
    def last_updated_by_crm_user_id(self) -> str | None:
        return self.progress.checked_by_crm_user_id if self.progress is not None else None

    @last_updated_by_crm_user_id.setter
    def last_updated_by_crm_user_id(self, value: str | None) -> None:
        self._ensure_progress().checked_by_crm_user_id = value

    @property
    def completed_at(self) -> datetime | None:
        return self.progress.checked_at if self.progress is not None else None

    @completed_at.setter
    def completed_at(self, value: datetime | None) -> None:
        self._ensure_progress().checked_at = value

    def _ensure_progress(self) -> SubtaskChecklistProgress:
        if self.progress is None:
            self.progress = SubtaskChecklistProgress()
        return self.progress


class SubtaskChecklistProgress(Base):
    """Execution value for a subtask checklist item."""

    __tablename__ = "subtask_checklist_progress"

    progress_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    checklist_item_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("subtask_checklist_items.checklist_item_id"),
        unique=True,
        index=True,
    )
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    item: Mapped[SubtaskItemValue] = relationship("SubtaskItemValue", back_populates="progress")


class SubtaskAssignment(Base):
    """Historical subtask assignment trace."""

    __tablename__ = "subtask_assignments"

    assignment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    subtask_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), index=True)
    assigned_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    assigned_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subtask: Mapped[Subtask] = relationship("Subtask", back_populates="assignments")

    @property
    def subtask_assignment_id(self) -> str:
        return self.assignment_id


class TaskComment(Base):
    """Comment attached to a task or subtask action."""

    __tablename__ = "task_comments"

    task_comment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    subtask_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), nullable=True, index=True)
    author_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    comment_type: Mapped[str] = mapped_column(String(50), default=TaskCommentType.GENERAL.value)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[Task] = relationship("Task", back_populates="comments")
    author: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[author_crm_user_id], lazy="joined")
    attachments: Mapped[list[TaskAttachment]] = relationship(
        "TaskAttachment",
        back_populates="comment",
        order_by="TaskAttachment.uploaded_at",
        lazy="selectin",
    )

    @property
    def author_display_name(self) -> str | None:
        return _user_display_label(self.author)


class TaskAttachment(Base):
    """Persisted multimedia associated to a task or subtask comment."""

    __tablename__ = "task_attachments"

    attachment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    subtask_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), nullable=True, index=True)
    task_comment_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("task_comments.task_comment_id"),
        nullable=True,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(500))
    file_url: Mapped[str] = mapped_column(String(1000))
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attachment_type: Mapped[str] = mapped_column(String(50), default=TaskAttachmentType.PHOTO.value)
    uploaded_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comment: Mapped[TaskComment | None] = relationship("TaskComment", back_populates="attachments")

    @property
    def id(self) -> str:
        return self.attachment_id

    @property
    def fileName(self) -> str:
        return self.file_name

    @property
    def fileType(self) -> str:
        return self.mime_type or "application/octet-stream"

    @property
    def kind(self) -> str:
        if self.attachment_type == TaskAttachmentType.PHOTO.value:
            return "image"
        if self.attachment_type == TaskAttachmentType.VIDEO.value:
            return "video"
        return "other"

    @property
    def previewUrl(self) -> str:
        return self.file_url

    @property
    def publicUrl(self) -> str:
        return self.file_url

    @property
    def storagePath(self) -> str:
        return self.file_url.lstrip("/")

    @property
    def size(self) -> int | None:
        return self.file_size_bytes

    @property
    def context(self) -> str:
        return "task"


class SubtaskTransition(Base):
    """Historical state transition for a subtask."""

    __tablename__ = "subtask_transitions"

    subtask_transition_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    subtask_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), index=True)
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    from_status: Mapped[str] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))
    performed_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    task_comment_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("task_comments.task_comment_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subtask: Mapped[Subtask] = relationship("Subtask", back_populates="transitions")
    performed_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[performed_by_crm_user_id], lazy="joined")

    @property
    def performed_by_display_name(self) -> str | None:
        return _user_display_label(self.performed_by_user)


class TaskAuditEvent(Base):
    """Structured audit event for task operations."""

    __tablename__ = "task_audit_events"

    task_audit_event_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id"), index=True)
    subtask_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("subtasks.subtask_id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[Task] = relationship("Task", back_populates="audit_events")


def _user_display_label(user: object | None) -> str | None:
    if user is None:
        return None
    display_name = getattr(user, "display_name", None)
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    email = getattr(user, "email", None)
    if isinstance(email, str) and email.strip():
        return email.strip()
    return None