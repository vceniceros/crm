"""Schemas for the task module."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from crm_backend.schemas.material_flow import (
    InventoryDispatchResponse,
    InventoryRequestResponse,
    RequiredMaterialResponse,
    RequiredMaterialWriteRequest,
)
from crm_backend.schemas.locations import LocationResponse


class TaskTemplateItemWriteRequest(BaseModel):
    item_label: str = Field(..., min_length=1, max_length=500)
    item_order: int = Field(..., ge=0)
    item_type: Literal["checkbox", "text"] = Field(default="checkbox")
    is_required: bool = Field(default=True)


class TaskTemplateSubtaskWriteRequest(BaseModel):
    subtask_title: str = Field(..., min_length=1, max_length=255)
    subtask_description: str | None = None
    order_index: int = Field(..., ge=0)
    responsible_role_key: str = Field(..., min_length=1, max_length=50)
    default_responsible_crm_user_id: str | None = None
    close_comment_required: bool = True
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    next_assignment_policy: Literal["role_queue_auto", "default_user_auto", "manual_required"] = Field(
        default="role_queue_auto"
    )
    subtask_type: Literal["standard", "pre_form"] = Field(default="standard")
    items: list[TaskTemplateItemWriteRequest] = Field(default_factory=list)


class PreFormFieldWriteRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    field_type: Literal["TEXT", "NUMBER", "TEXTAREA", "DATE", "TEL", "FILE", "CHECKBOX"] = Field(default="TEXT")
    is_required: bool = Field(default=True)
    order_index: int = Field(..., ge=0)
    placeholder: str | None = Field(default=None, max_length=255)


class PreFormDefinitionWriteRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    instructions: str | None = None
    fields: list[PreFormFieldWriteRequest] = Field(default_factory=list)


class CreateTaskTemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    requires_pre_form: bool = False
    pre_form: PreFormDefinitionWriteRequest | None = None
    subtasks: list[TaskTemplateSubtaskWriteRequest] = Field(..., min_length=1)
    required_materials: list[RequiredMaterialWriteRequest] = Field(default_factory=list)


class UpdateTaskTemplateRequest(CreateTaskTemplateRequest):
    pass


class SetTaskTemplateActivationRequest(BaseModel):
    is_active: bool


class RequiredMaterialItem(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class CreateTaskFromTemplateRequest(BaseModel):
    template_id: str
    client_id: str
    location_id: str | None = None
    task_title: str | None = Field(default=None, min_length=1, max_length=255)
    task_description: str | None = None
    requires_arrival_comment: bool | None = None
    requires_video_evidence: bool | None = None
    extra_materials: list[RequiredMaterialItem] = Field(default_factory=list)


class UpdateSubtaskItemValueRequest(BaseModel):
    item_id: str
    checkbox_value: bool | None = None
    text_value: str | None = None


class UpdateSubtaskProgressRequest(BaseModel):
    items: list[UpdateSubtaskItemValueRequest] = Field(..., min_length=1)


class ExecuteSubtaskActionRequest(BaseModel):
    action: Literal["close_subtask", "reject_subtask", "put_on_hold"]
    comment: str = Field(..., min_length=1)
    next_assigned_crm_user_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)


class AssignSubtaskRequest(BaseModel):
    assigned_crm_user_id: str = Field(..., min_length=1)
    notes: str | None = None


class ApproveTaskRequest(BaseModel):
    comment: str | None = None


class RejectTaskApprovalRequest(BaseModel):
    comment: str = Field(..., min_length=1)


class CreateTaskCommentRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    location_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    mentioned_user_ids: list[str] = Field(default_factory=list)


class TaskAttachmentResponse(BaseModel):
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


class TaskCommentMentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_comment_mention_id: str
    mentioned_crm_user_id: str
    mentioned_display_name: str | None = None
    mentioned_email: str | None = None
    created_by_crm_user_id: str
    created_at: datetime


class TaskTemplateItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_template_item_id: str
    item_label: str
    item_order: int
    item_type: str
    is_required: bool


class TaskTemplateSubtaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_template_subtask_id: str
    subtask_title: str
    subtask_description: str | None
    order_index: int
    responsible_role_key: str
    default_responsible_crm_user_id: str | None
    close_comment_required: bool
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    next_assignment_policy: str
    subtask_type: str
    items: list[TaskTemplateItemResponse]


class PreFormFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    label: str
    field_type: str
    is_required: bool
    order_index: int
    placeholder: str | None


class PreFormDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    form_id: str
    title: str | None
    instructions: str | None
    fields: list[PreFormFieldResponse] = Field(default_factory=list)


class TaskTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: str
    template_name: str
    description: str | None
    is_active: bool
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    requires_pre_form: bool = False
    created_by_crm_user_id: str
    created_at: datetime
    updated_at: datetime | None
    required_materials: list[RequiredMaterialResponse]
    pre_form: PreFormDefinitionResponse | None = None
    subtasks: list[TaskTemplateSubtaskResponse]


class TaskSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    client_id: str
    client_name: str
    location_id: str | None
    template_id: str
    template_name: str
    task_title: str
    task_description: str | None
    status: str
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    arrival_registered_at: datetime | None = None
    arrival_comment_id: str | None = None
    current_subtask_id: str | None
    current_assigned_crm_user_id: str | None
    current_assigned_user_display_name: str | None = None
    location: LocationResponse | None = None
    created_at: datetime
    updated_at: datetime | None


class UnassignedSubtaskQueueResponse(BaseModel):
    task_id: str
    client_id: str
    client_name: str
    template_id: str
    template_name: str
    task_title: str
    subtask_id: str
    subtask_title: str
    responsible_role_key: str
    status: str
    order_index: int


class SubtaskItemValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subtask_item_value_id: str
    item_label: str
    item_order: int
    item_type: str
    is_required: bool
    checkbox_value: bool
    text_value: str | None
    last_updated_by_crm_user_id: str | None
    completed_at: datetime | None


class SubtaskAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subtask_assignment_id: str
    assigned_crm_user_id: str
    assigned_user_display_name: str | None = None
    assigned_by_crm_user_id: str | None
    notes: str | None
    assigned_at: datetime


class SubtaskTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subtask_transition_id: str
    from_status: str
    to_status: str
    action: str
    performed_by_crm_user_id: str
    performed_by_display_name: str | None = None
    task_comment_id: str | None
    created_at: datetime


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_comment_id: str
    subtask_id: str | None
    author_crm_user_id: str
    author_display_name: str | None = None
    comment_type: str
    body: str
    location: LocationResponse | None = None
    created_at: datetime
    attachments: list[TaskAttachmentResponse] = Field(default_factory=list)
    mentions: list[TaskCommentMentionResponse] = Field(default_factory=list)


class TaskAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_audit_event_id: str
    subtask_id: str | None
    event_type: str
    actor_crm_user_id: str
    payload_json: dict[str, object]
    created_at: datetime


class TaskExtraMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    required_material_id: str
    product_id: str
    product_code: str
    product_name: str
    quantity: int
    requires_tracking: bool


class SubtaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subtask_id: str
    template_subtask_id: str
    subtask_title: str
    subtask_description: str | None
    order_index: int
    responsible_role_key: str
    assigned_crm_user_id: str | None
    assigned_user_display_name: str | None = None
    default_responsible_crm_user_id: str | None
    default_assigned_user_display_name: str | None = None
    close_comment_required: bool
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    next_assignment_policy: str
    subtask_type: str
    status: str
    completed_at: datetime | None
    closed_by_crm_user_id: str | None
    closed_by_display_name: str | None = None
    items: list[SubtaskItemValueResponse]
    assignments: list[SubtaskAssignmentResponse]
    transitions: list[SubtaskTransitionResponse]


class TaskDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    client_id: str
    client_name: str
    location_id: str | None
    template_id: str
    template_name: str
    task_title: str
    task_description: str | None
    status: str
    requires_arrival_comment: bool = False
    requires_video_evidence: bool = False
    arrival_registered_at: datetime | None = None
    arrival_comment_id: str | None = None
    current_subtask_id: str | None
    current_assigned_crm_user_id: str | None
    current_assigned_user_display_name: str | None = None
    location: LocationResponse | None = None
    created_by_crm_user_id: str
    finalized_by_crm_user_id: str | None
    finalized_by_display_name: str | None = None
    finalized_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    required_materials: list[RequiredMaterialResponse]
    extra_materials: list[TaskExtraMaterialResponse] = Field(default_factory=list)
    inventory_requests: list[InventoryRequestResponse]
    dispatches: list[InventoryDispatchResponse]
    subtasks: list[SubtaskResponse]
    comments: list[TaskCommentResponse]
    audit_events: list[TaskAuditEventResponse]


class GenerateTaskSatisfactionFormResponse(BaseModel):
    form_id: str
    task_id: str
    public_link_token: str
    survey_path: str
    expires_at: datetime
    status_label: str


class TaskSatisfactionFormStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    form_id: str
    task_id: str
    status_label: str
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    has_response: bool

    @classmethod
    def from_orm_form(cls, form: Any) -> "TaskSatisfactionFormStatusResponse":
        return cls(
            form_id=form.form_id,
            task_id=form.task_id,
            status_label=form.status_label,
            expires_at=form.expires_at,
            used_at=form.used_at,
            revoked_at=form.revoked_at,
            created_at=form.created_at,
            has_response=form.response is not None,
        )


class TaskSatisfactionResponseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response_id: str
    task_id: str
    customer_name: str
    customer_company: str
    rating: float
    comment: str | None
    submitted_at: datetime


class PublicTaskSatisfactionFormInfoResponse(BaseModel):
    task_title: str
    client_name: str | None
    location_name: str | None
    status_label: str


class SubmitTaskSatisfactionFormRequest(BaseModel):
    rating: float = Field(..., ge=0.5, le=5.0)
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_company: str = Field(..., min_length=1, max_length=255)
    comment: str | None = Field(default=None, max_length=2000)


class TaskPreFormFieldValueWriteRequest(BaseModel):
    field_id: str
    text_value: str | None = None


class TaskPreFormFieldValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    label: str
    field_type: str
    text_value: str | None
    file_attachment_id: str | None


class TaskPreFormStatusResponse(BaseModel):
    instance_id: str
    task_id: str
    status_label: str
    expires_at: datetime
    submitted_at: datetime | None
    revoked_at: datetime | None
    form_link_path: str | None
    response_values: list[TaskPreFormFieldValueResponse] = Field(default_factory=list)


class PublicTaskPreFormInfoResponse(BaseModel):
    task_title: str
    client_name: str | None
    location_name: str | None
    title: str | None
    instructions: str | None
    fields: list[PreFormFieldResponse] = Field(default_factory=list)


class SubmitTaskPreFormRequest(BaseModel):
    values: list[TaskPreFormFieldValueWriteRequest] = Field(default_factory=list)
