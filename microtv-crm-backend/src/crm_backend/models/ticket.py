"""Ticket domain models for operational incident tracking."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.crm_role import CrmRole
    from crm_backend.models.crm_user import CrmUser
    from crm_backend.models.material_flow import InventoryDispatch, InventoryRequest, TicketRequiredMaterial
    from crm_backend.models.settings import CrmCategory
    from crm_backend.models.task_reference import Client, Location


class TicketStatus(StrEnum):
    """Supported ticket lifecycle states."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CLOSED = "CLOSED"


class TicketPriority(StrEnum):
    """Supported ticket priority values."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketCommentType(StrEnum):
    """Comment types used by ticket timeline."""

    GENERAL = "general"
    SYSTEM = "system"
    CLOSURE = "closure"
    ARRIVAL_REGISTRATION = "arrival_registration"
    CLOSURE_EVIDENCE = "closure_evidence"


class TicketAttachmentType(StrEnum):
    """Supported persisted attachment types."""

    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class TicketTransitionAction(StrEnum):
    """Supported explicit status transition actions."""

    START_WORK = "start_work"
    PUT_ON_HOLD = "put_on_hold"
    MARK_RESOLVED = "mark_resolved"
    SUBMIT_FOR_APPROVAL = "submit_for_approval"
    APPROVE_CLOSE = "approve_close"
    REJECT_CLOSE = "reject_close"
    REOPEN = "reopen"
    CLOSE = "close"


class Ticket(Base):
    """Operational ticket aggregate root."""

    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    legacy_ticket_title: Mapped[str | None] = mapped_column("ticket_title", String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    legacy_ticket_description: Mapped[str | None] = mapped_column("ticket_description", Text, nullable=True)
    client_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("clients.client_id"), index=True)
    location_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("locations.location_id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=TicketStatus.OPEN.value, index=True)
    legacy_status_id: Mapped[str | None] = mapped_column("status_id", Uuid(as_uuid=False), nullable=True)
    priority: Mapped[str] = mapped_column(String(30), default=TicketPriority.MEDIUM.value, server_default=TicketPriority.MEDIUM.value)
    legacy_priority_id: Mapped[str | None] = mapped_column("priority_id", Uuid(as_uuid=False), nullable=True)
    assigned_role_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_roles.crm_role_id"), nullable=True, index=True)
    assigned_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True, index=True)
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    resolved_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_arrival_comment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    arrival_registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_comment_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey(
            "ticket_comments.ticket_comment_id",
            ondelete="SET NULL",
            name="fk_tickets_arrival_comment",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    solution_comment_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey(
            "ticket_comments.ticket_comment_id",
            ondelete="SET NULL",
            name="fk_tickets_solution_comment",
            use_alter=True,
        ),
        nullable=True,
        index=True,
    )
    requires_video_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_categories.category_id"), nullable=True, index=True)

    client: Mapped["Client"] = relationship("Client", lazy="joined")
    location: Mapped["Location"] = relationship("Location", lazy="joined")
    category: Mapped["CrmCategory | None"] = relationship("CrmCategory", foreign_keys=[category_id], lazy="joined")
    assigned_role: Mapped["CrmRole | None"] = relationship("CrmRole", foreign_keys=[assigned_role_id], lazy="joined")
    assigned_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[assigned_user_id], lazy="joined")
    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_crm_user_id], lazy="joined")
    resolved_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[resolved_by_crm_user_id], lazy="joined")
    closed_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[closed_by_crm_user_id], lazy="joined")
    solution_comment: Mapped["TicketComment | None"] = relationship(
        "TicketComment",
        foreign_keys=[solution_comment_id],
        lazy="joined",
    )

    comments: Mapped[list[TicketComment]] = relationship(
        "TicketComment",
        back_populates="ticket",
        foreign_keys="TicketComment.ticket_id",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
        lazy="selectin",
    )
    attachments: Mapped[list[TicketAttachment]] = relationship(
        "TicketAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAttachment.uploaded_at",
        lazy="selectin",
    )
    status_history: Mapped[list[TicketStatusTransition]] = relationship(
        "TicketStatusTransition",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketStatusTransition.created_at",
        lazy="selectin",
    )
    assignment_history: Mapped[list[TicketAssignmentHistory]] = relationship(
        "TicketAssignmentHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAssignmentHistory.created_at",
        lazy="selectin",
    )
    collaborators: Mapped[list["TicketCollaborator"]] = relationship(
        "TicketCollaborator",
        back_populates="ticket",
        primaryjoin="and_(Ticket.ticket_id == TicketCollaborator.ticket_id, TicketCollaborator.deleted_at.is_(None))",
        cascade="all, delete-orphan",
        order_by="TicketCollaborator.created_at",
        lazy="selectin",
    )
    audit_events: Mapped[list[TicketAuditEvent]] = relationship(
        "TicketAuditEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAuditEvent.created_at",
        lazy="selectin",
    )
    required_materials: Mapped[list["TicketRequiredMaterial"]] = relationship(
        "TicketRequiredMaterial",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketRequiredMaterial.created_at",
        lazy="selectin",
    )
    inventory_requests: Mapped[list["InventoryRequest"]] = relationship(
        "InventoryRequest",
        primaryjoin="foreign(InventoryRequest.external_ticket_id) == Ticket.ticket_id.cast(String)",
        viewonly=True,
        order_by="InventoryRequest.requested_at.desc()",
        lazy="selectin",
    )
    dispatches: Mapped[list["InventoryDispatch"]] = relationship(
        "InventoryDispatch",
        primaryjoin="foreign(InventoryDispatch.external_ticket_id) == Ticket.ticket_id.cast(String)",
        viewonly=True,
        order_by="InventoryDispatch.created_at.desc()",
        lazy="selectin",
    )
    satisfaction_forms: Mapped[list["TicketSatisfactionForm"]] = relationship(
        "TicketSatisfactionForm",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketSatisfactionForm.created_at.desc()",
        lazy="selectin",
    )

    @property
    def client_name(self) -> str:
        return self.client.business_name

    @property
    def category_name(self) -> str | None:
        return getattr(self.category, "name", None)

    @property
    def assigned_role_key(self) -> str | None:
        return _normalize_role_key(getattr(self.assigned_role, "role_key", None))

    @property
    def assigned_role_label(self) -> str | None:
        role_label = getattr(self.assigned_role, "role_label", None)
        if isinstance(role_label, str) and role_label.strip():
            return role_label.strip()
        return self.assigned_role_key

    @property
    def assigned_user_display_name(self) -> str | None:
        return _user_display_label(self.assigned_user)

    @property
    def created_by_display_name(self) -> str | None:
        return _user_display_label(self.created_by_user)

    @property
    def resolved_by_display_name(self) -> str | None:
        return _user_display_label(self.resolved_by_user)

    @property
    def closed_by_display_name(self) -> str | None:
        return _user_display_label(self.closed_by_user)

    @property
    def approved_by_executive(self) -> bool:
        if self.status != TicketStatus.CLOSED.value:
            return False
        if any(transition.action == TicketTransitionAction.APPROVE_CLOSE.value for transition in self.status_history):
            return True
        return any(event.event_type == "ticket.approved_by_executive" for event in self.audit_events)

    @property
    def latest_satisfaction_form(self) -> "TicketSatisfactionForm | None":
        if not self.satisfaction_forms:
            return None
        return self.satisfaction_forms[0]

    @property
    def survey_generated_at(self) -> datetime | None:
        latest_form = self.latest_satisfaction_form
        if latest_form is None:
            return None
        return latest_form.created_at

    @property
    def survey_completed_at(self) -> datetime | None:
        latest_form = self.latest_satisfaction_form
        if latest_form is None:
            return None
        return latest_form.used_at

    @property
    def survey_status_label(self) -> str | None:
        latest_form = self.latest_satisfaction_form
        if latest_form is None:
            return None
        return latest_form.status_label

    @property
    def has_active_survey(self) -> bool:
        latest_form = self.latest_satisfaction_form
        if latest_form is None:
            return False
        return latest_form.is_usable


class TicketComment(Base):
    """Comment attached to a ticket timeline."""

    __tablename__ = "ticket_comments"

    ticket_comment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    author_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    location_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("locations.location_id"), nullable=True, index=True)
    comment_type: Mapped[str] = mapped_column(String(30), default=TicketCommentType.GENERAL.value, index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="comments", foreign_keys=[ticket_id])
    author: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[author_crm_user_id], lazy="joined")
    location: Mapped["Location | None"] = relationship("Location", foreign_keys=[location_id], lazy="joined")
    attachments: Mapped[list[TicketAttachment]] = relationship(
        "TicketAttachment",
        back_populates="comment",
        order_by="TicketAttachment.uploaded_at",
        lazy="selectin",
    )
    mentions: Mapped[list["TicketCommentMention"]] = relationship(
        "TicketCommentMention",
        back_populates="comment",
        cascade="all, delete-orphan",
        order_by="TicketCommentMention.created_at",
        lazy="selectin",
    )

    @property
    def author_display_name(self) -> str | None:
        return _user_display_label(self.author)


class TicketCommentMention(Base):
    """User explicitly mentioned in a ticket comment."""

    __tablename__ = "ticket_comment_mentions"
    __table_args__ = (
        UniqueConstraint("ticket_comment_id", "mentioned_crm_user_id", name="uq_ticket_comment_mentions_comment_user"),
    )

    ticket_comment_mention_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_comment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("ticket_comments.ticket_comment_id", ondelete="CASCADE"), index=True)
    mentioned_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id", ondelete="CASCADE"), index=True)
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comment: Mapped[TicketComment] = relationship("TicketComment", back_populates="mentions")
    mentioned_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[mentioned_crm_user_id], lazy="joined")
    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_crm_user_id], lazy="joined")

    @property
    def mentioned_display_name(self) -> str | None:
        return _user_display_label(self.mentioned_user)

    @property
    def mentioned_email(self) -> str | None:
        return getattr(self.mentioned_user, "email", None)


class TicketCollaborator(Base):
    """User with operational access to a ticket beyond the primary assignee."""

    __tablename__ = "ticket_collaborators"
    __table_args__ = (
        Index("idx_ticket_collaborators_ticket", "ticket_id"),
        Index("idx_ticket_collaborators_user", "crm_user_id"),
    )

    ticket_collaborator_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), index=True)
    crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(30), default="manual", index=True)
    added_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="collaborators")
    crm_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[crm_user_id], lazy="joined")
    added_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[added_by_crm_user_id], lazy="joined")

    @property
    def display_name(self) -> str | None:
        return _user_display_label(self.crm_user)

    @property
    def email(self) -> str | None:
        return getattr(self.crm_user, "email", None)


class TicketAttachment(Base):
    """Persisted multimedia associated to a ticket comment."""

    __tablename__ = "ticket_attachments"

    attachment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    ticket_comment_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("ticket_comments.ticket_comment_id"),
        nullable=True,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(500))
    file_url: Mapped[str] = mapped_column(String(1000))
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attachment_type: Mapped[str] = mapped_column(String(50), default=TicketAttachmentType.PHOTO.value)
    uploaded_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="attachments")
    comment: Mapped[TicketComment | None] = relationship("TicketComment", back_populates="attachments")

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
        if self.attachment_type == TicketAttachmentType.PHOTO.value:
            return "image"
        if self.attachment_type == TicketAttachmentType.VIDEO.value:
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
        return "ticket"


class TicketStatusTransition(Base):
    """Historical status transition for ticket lifecycle."""

    __tablename__ = "ticket_status_transitions"

    ticket_status_transition_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    from_status: Mapped[str] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(50))
    performed_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    ticket_comment_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("ticket_comments.ticket_comment_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="status_history")
    performed_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[performed_by_crm_user_id], lazy="joined")

    @property
    def performed_by_display_name(self) -> str | None:
        return _user_display_label(self.performed_by_user)


class TicketAssignmentHistory(Base):
    """Historical assignment trace for role/user reassignment."""

    __tablename__ = "ticket_assignment_history"

    ticket_assignment_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    previous_role_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_roles.crm_role_id"), nullable=True)
    previous_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    assigned_role_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_roles.crm_role_id"), nullable=True, index=True)
    assigned_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True, index=True)
    assigned_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="assignment_history")
    previous_role: Mapped["CrmRole | None"] = relationship("CrmRole", foreign_keys=[previous_role_id], lazy="joined")
    previous_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[previous_user_id], lazy="joined")
    assigned_role: Mapped["CrmRole | None"] = relationship("CrmRole", foreign_keys=[assigned_role_id], lazy="joined")
    assigned_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[assigned_user_id], lazy="joined")
    assigned_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[assigned_by_crm_user_id], lazy="joined")

    @property
    def previous_role_key(self) -> str | None:
        return _normalize_role_key(getattr(self.previous_role, "role_key", None))

    @property
    def assigned_role_key(self) -> str | None:
        return _normalize_role_key(getattr(self.assigned_role, "role_key", None))

    @property
    def previous_user_display_name(self) -> str | None:
        return _user_display_label(self.previous_user)

    @property
    def assigned_user_display_name(self) -> str | None:
        return _user_display_label(self.assigned_user)

    @property
    def assigned_by_display_name(self) -> str | None:
        return _user_display_label(self.assigned_by_user)


class TicketAuditEvent(Base):
    """Structured audit event for ticket operations."""

    __tablename__ = "ticket_audit_events"

    ticket_audit_event_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="audit_events")


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


def _normalize_role_key(role_key: str | None) -> str | None:
    if not isinstance(role_key, str):
        return None
    normalized = role_key.strip()
    if normalized == "admin_crm":
        return "admin"
    if normalized == "tecnico_campo":
        return "tecnico"
    if normalized == "encargado_deposito":
        return "deposito"
    return normalized or None


# ---------------------------------------------------------------------------
# Satisfaction forms (US-2: formulario de satisfacción del cliente)
# ---------------------------------------------------------------------------


class TicketSatisfactionForm(Base):
    """Secure one-use satisfaction form generated for a closed ticket."""

    __tablename__ = "ticket_satisfaction_forms"

    form_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    # SHA-256 hex digest of the raw opaque token — never store the raw token.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_by_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["Ticket"] = relationship("Ticket", foreign_keys=[ticket_id], back_populates="satisfaction_forms", lazy="joined")
    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_user_id], lazy="joined")
    response: Mapped["TicketSatisfactionResponse | None"] = relationship(
        "TicketSatisfactionResponse",
        back_populates="form",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_expired(self) -> bool:
        from datetime import timezone as _tz

        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # SQLite can return naive datetimes even when timezone=True.
            expires_at = expires_at.replace(tzinfo=_tz.utc)

        return datetime.now(_tz.utc) > expires_at

    @property
    def is_usable(self) -> bool:
        return self.revoked_at is None and self.used_at is None and not self.is_expired

    @property
    def status_label(self) -> str:
        if self.revoked_at is not None:
            return "revocado"
        if self.used_at is not None:
            return "respondido"
        if self.is_expired:
            return "expirado"
        return "pendiente"


class TicketSatisfactionResponse(Base):
    """Client response to a satisfaction form."""

    __tablename__ = "ticket_satisfaction_responses"

    response_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    form_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("ticket_satisfaction_forms.form_id"), unique=True, index=True)
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_company: Mapped[str] = mapped_column(String(255), nullable=False)
    # Rating: 0.5 to 5.0 stored as NUMERIC(3,1)
    rating: Mapped[float] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Basic audit — hashed IP and user-agent, never raw IP.
    submitter_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitter_user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    form: Mapped["TicketSatisfactionForm"] = relationship("TicketSatisfactionForm", back_populates="response")
    media: Mapped[list["TicketSatisfactionMedia"]] = relationship(
        "TicketSatisfactionMedia",
        back_populates="response",
        cascade="all, delete-orphan",
        order_by="TicketSatisfactionMedia.created_at",
        lazy="selectin",
    )


class TicketSatisfactionMedia(Base):
    """Multimedia attached to a satisfaction response."""

    __tablename__ = "ticket_satisfaction_media"

    media_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    response_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("ticket_satisfaction_responses.response_id"), index=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    file_name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped["TicketSatisfactionResponse"] = relationship("TicketSatisfactionResponse", back_populates="media")
