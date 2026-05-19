"""Schemas for the ticket module."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from crm_backend.schemas.locations import LocationResponse
from crm_backend.schemas.material_flow import InventoryDispatchResponse, InventoryRequestResponse


TicketStatusLiteral = Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "PENDING_APPROVAL", "CLOSED"]
TicketPriorityLiteral = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
TicketCommentTypeLiteral = Literal["general", "system", "closure", "arrival_registration", "closure_evidence"]


class RequiredMaterialItem(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class CreateTicketRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    client_id: str
    location_id: str | None = None
    description: str = Field(..., min_length=1)
    priority: TicketPriorityLiteral = "MEDIUM"
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = True
    assigned_role_id: str | None = None
    assigned_user_id: str | None = None
    collaborator_user_ids: list[str] = Field(default_factory=list)
    required_materials: list[RequiredMaterialItem] = Field(default_factory=list)


class AssignTicketRequest(BaseModel):
    assigned_role_id: str | None = None
    assigned_user_id: str | None = None
    collaborator_user_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class CreateTicketCommentRequest(BaseModel):
    body: str = Field(..., min_length=1)
    location_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    mentioned_user_ids: list[str] = Field(default_factory=list)


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


class TicketCommentMentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_comment_mention_id: str
    mentioned_crm_user_id: str
    mentioned_display_name: str | None = None
    mentioned_email: str | None = None
    created_by_crm_user_id: str
    created_at: datetime


class TicketCollaboratorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_collaborator_id: str
    ticket_id: str
    crm_user_id: str
    display_name: str | None = None
    email: str | None = None
    source: str
    added_by_crm_user_id: str | None = None
    created_at: datetime


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
    mentions: list[TicketCommentMentionResponse] = Field(default_factory=list)


class TicketRequiredMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    required_material_id: str
    product_id: str
    product_code: str
    product_name: str
    quantity: int
    requires_tracking: bool


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
    collaborators: list[TicketCollaboratorResponse] = Field(default_factory=list)
    created_by_crm_user_id: str
    created_by_display_name: str | None = None
    resolved_by_crm_user_id: str | None
    resolved_by_display_name: str | None = None
    resolved_at: datetime | None
    closed_by_crm_user_id: str | None
    closed_by_display_name: str | None = None
    closed_at: datetime | None
    approved_by_executive: bool = False
    survey_generated_at: datetime | None = None
    survey_completed_at: datetime | None = None
    survey_status_label: str | None = None
    has_active_survey: bool = False
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = True
    arrival_registered_at: datetime | None = None
    arrival_comment_id: str | None = None
    solution_comment_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketSummaryResponse):
    has_arrival_registered: bool = False
    can_register_arrival: bool = False
    required_materials: list[TicketRequiredMaterialResponse] = Field(default_factory=list)
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


# ---------------------------------------------------------------------------
# Arrival registration (US-1)
# ---------------------------------------------------------------------------


class RegisterArrivalRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    attachment_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Satisfaction form (US-2)
# ---------------------------------------------------------------------------


class GenerateSatisfactionFormRequest(BaseModel):
    """No body needed — ticket_id is in path. Placeholder for future fields."""
    pass


class SatisfactionFormStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    form_id: str
    ticket_id: str
    status_label: str
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    has_response: bool

    @classmethod
    def from_orm_form(cls, form) -> "SatisfactionFormStatusResponse":
        return cls(
            form_id=form.form_id,
            ticket_id=form.ticket_id,
            status_label=form.status_label,
            expires_at=form.expires_at,
            used_at=form.used_at,
            revoked_at=form.revoked_at,
            created_at=form.created_at,
            has_response=form.response is not None,
        )


class GenerateSatisfactionFormResponse(BaseModel):
    """Returned once only — includes raw token for the satisfaction link."""
    form_id: str
    ticket_id: str
    public_link_token: str  # The raw opaque token — shown once.
    survey_path: str
    expires_at: datetime
    status_label: str


class PublicSatisfactionFormInfoResponse(BaseModel):
    """Safe public response — no IDs, no sensitive data."""
    ticket_number: str
    client_name: str | None
    location_name: str | None
    status_label: str


class SubmitSatisfactionFormRequest(BaseModel):
    rating: float = Field(..., ge=0.5, le=5.0)
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_company: str = Field(..., min_length=1, max_length=255)
    comment: str | None = Field(default=None, max_length=2000)


class SatisfactionMediaFileResponse(BaseModel):
    id: str
    survey_id: str
    file_path: str
    file_type: str
    file_name: str | None = None
    size_bytes: int | None = None

    @classmethod
    def from_orm_media(cls, media: Any) -> "SatisfactionMediaFileResponse":
        response = getattr(media, "response", None)
        survey_id = getattr(media, "survey_id", None) or getattr(response, "form_id", "")
        return cls(
            id=str(getattr(media, "media_id", "")),
            survey_id=str(survey_id),
            file_path=str(getattr(media, "file_path", "")),
            file_type=str(getattr(media, "mime_type", "application/octet-stream")),
            file_name=getattr(media, "file_name", None),
            size_bytes=getattr(media, "size_bytes", None),
        )


class SatisfactionResponseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response_id: str
    ticket_id: str
    customer_name: str
    customer_company: str
    rating: float
    comment: str | None
    submitted_at: datetime
    media_count: int
    media_files: list[SatisfactionMediaFileResponse] = Field(default_factory=list)

    @classmethod
    def from_orm_response(cls, response: Any) -> "SatisfactionResponseDetailResponse":
        media_files = [
            SatisfactionMediaFileResponse.from_orm_media(media)
            for media in (getattr(response, "media", None) or [])
        ]
        return cls(
            response_id=response.response_id,
            ticket_id=response.ticket_id,
            customer_name=response.customer_name,
            customer_company=response.customer_company,
            rating=response.rating,
            comment=response.comment,
            submitted_at=response.submitted_at,
            media_count=len(media_files),
            media_files=media_files,
        )
