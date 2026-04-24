"""Schemas for the ticket module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from crm_backend.schemas.locations import LocationResponse
from crm_backend.schemas.material_flow import InventoryDispatchResponse, InventoryRequestResponse


TicketStatusLiteral = Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "PENDING_APPROVAL", "CLOSED"]
TicketPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
TicketCommentTypeLiteral = Literal["general", "system", "closure"]


class CreateTicketRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    client_id: str
    location_id: str | None = None
    description: str = Field(..., min_length=1)
    priority: TicketPriorityLiteral = "MEDIUM"
    assigned_role_id: str | None = None
    assigned_user_id: str | None = None


class AssignTicketRequest(BaseModel):
    assigned_role_id: str | None = None
    assigned_user_id: str | None = None
    notes: str | None = None


class CreateTicketCommentRequest(BaseModel):
    body: str = Field(..., min_length=1)
    location_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)


class UpdateTicketStatusRequest(BaseModel):
    to_status: Literal["IN_PROGRESS", "ON_HOLD", "RESOLVED", "OPEN"]
    comment: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)


class CloseTicketRequest(BaseModel):
    comment: str
    attachment_ids: list[str] = Field(default_factory=list)


class ApproveTicketRequest(BaseModel):
    comment: str | None = None


class RejectTicketApprovalRequest(BaseModel):
    comment: str = Field(..., min_length=1)


class ReopenTicketRequest(BaseModel):
    comment: str = Field(..., min_length=1)


class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fileName: str
    fileType: str
    kind: str
    context: str
    previewUrl: str
    publicUrl: str
    storagePath: str
    size: int | None


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_comment_id: str
    author_crm_user_id: str
    author_display_name: str | None = None
    comment_type: str
    body: str
    created_at: datetime
    location: LocationResponse | None = None
    attachments: list[TicketAttachmentResponse] = Field(default_factory=list)


class TicketStatusTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_status_transition_id: str
    from_status: str
    to_status: str
    action: str
    performed_by_crm_user_id: str
    performed_by_display_name: str | None = None
    ticket_comment_id: str | None
    created_at: datetime


class TicketAssignmentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_assignment_id: str
    previous_role_id: str | None
    previous_role_key: str | None = None
    previous_user_id: str | None
    previous_user_display_name: str | None = None
    assigned_role_id: str | None
    assigned_role_key: str | None = None
    assigned_user_id: str | None
    assigned_user_display_name: str | None = None
    assigned_by_crm_user_id: str
    assigned_by_display_name: str | None = None
    notes: str | None
    created_at: datetime


class TicketAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_audit_event_id: str
    event_type: str
    actor_crm_user_id: str
    payload_json: dict[str, object]
    created_at: datetime


class TicketSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    ticket_number: str
    title: str
    description: str
    client_id: str
    client_name: str
    location_id: str
    location: LocationResponse | None = None
    status: str
    priority: str
    assigned_role_id: str | None
    assigned_role_key: str | None = None
    assigned_role_label: str | None = None
    assigned_user_id: str | None
    assigned_user_display_name: str | None = None
    created_by_crm_user_id: str
    created_by_display_name: str | None = None
    resolved_by_crm_user_id: str | None
    resolved_by_display_name: str | None = None
    resolved_at: datetime | None
    closed_by_crm_user_id: str | None
    closed_by_display_name: str | None = None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketSummaryResponse):
    comments: list[TicketCommentResponse] = Field(default_factory=list)
    status_history: list[TicketStatusTransitionResponse] = Field(default_factory=list)
    assignment_history: list[TicketAssignmentHistoryResponse] = Field(default_factory=list)
    audit_events: list[TicketAuditEventResponse] = Field(default_factory=list)
    inventory_requests: list[InventoryRequestResponse] = Field(default_factory=list)
    dispatches: list[InventoryDispatchResponse] = Field(default_factory=list)


class TicketRoleOptionResponse(BaseModel):
    crm_role_id: str
    role_key: str
    role_label: str
