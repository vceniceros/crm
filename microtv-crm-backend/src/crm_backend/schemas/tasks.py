"""Schemas for the task module."""

from __future__ import annotations

from datetime import datetime
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
    next_assignment_policy: Literal["role_queue_auto", "default_user_auto", "manual_required"] = Field(
        default="role_queue_auto"
    )
    items: list[TaskTemplateItemWriteRequest] = Field(default_factory=list)


class CreateTaskTemplateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    subtasks: list[TaskTemplateSubtaskWriteRequest] = Field(..., min_length=1)
    required_materials: list[RequiredMaterialWriteRequest] = Field(default_factory=list)


class UpdateTaskTemplateRequest(CreateTaskTemplateRequest):
    pass


class SetTaskTemplateActivationRequest(BaseModel):
    is_active: bool


class CreateTaskFromTemplateRequest(BaseModel):
    template_id: str
    client_id: str
    location_id: str | None = None
    task_title: str | None = Field(default=None, min_length=1, max_length=255)
    task_description: str | None = None


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
    next_assignment_policy: str
    items: list[TaskTemplateItemResponse]


class TaskTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: str
    template_name: str
    description: str | None
    is_active: bool
    created_by_crm_user_id: str
    created_at: datetime
    updated_at: datetime | None
    required_materials: list[RequiredMaterialResponse]
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
    created_at: datetime
    attachments: list[TaskAttachmentResponse] = Field(default_factory=list)


class TaskAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_audit_event_id: str
    subtask_id: str | None
    event_type: str
    actor_crm_user_id: str
    payload_json: dict[str, object]
    created_at: datetime


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
    next_assignment_policy: str
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
    inventory_requests: list[InventoryRequestResponse]
    dispatches: list[InventoryDispatchResponse]
    subtasks: list[SubtaskResponse]
    comments: list[TaskCommentResponse]
    audit_events: list[TaskAuditEventResponse]