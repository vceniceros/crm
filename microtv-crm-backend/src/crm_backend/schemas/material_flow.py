"""Schemas for template materials, requests, and dispatch flows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequiredMaterialWriteRequest(BaseModel):
    product_id: str
    quantity_required: int = Field(..., gt=0)
    notes: str | None = None


class RequiredMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    required_material_id: str
    product_id: str
    product_code: str
    product_name: str
    quantity_required: float
    notes: str | None
    requires_tracking: bool


class InventoryRequestItemWriteRequest(BaseModel):
    product_id: str
    quantity_requested: int = Field(..., gt=0)
    notes: str | None = None


class CreateInventoryRequestRequest(BaseModel):
    source_type: Literal["TASK", "TICKET"]
    task_id: str | None = None
    external_ticket_id: str | None = None
    request_reason: str | None = None
    items: list[InventoryRequestItemWriteRequest] = Field(..., min_length=1)


class ReviewInventoryRequestRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    review_notes: str | None = None


class InventoryDispatchItemWriteRequest(BaseModel):
    product_id: str
    quantity_dispatched: int = Field(..., gt=0)
    serial_number: str | None = Field(default=None, max_length=255)
    barcode_value: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class CreateTaskDispatchRequest(BaseModel):
    request_id: str | None = None
    dispatch_notes: str | None = None
    items: list[InventoryDispatchItemWriteRequest] = Field(..., min_length=1)


class ConfirmDispatchItemRequest(BaseModel):
    confirmation_type: Literal["received", "delivered", "installed"]


class InventoryRequestItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_request_item_id: str
    product_id: str
    product_code: str
    product_name: str
    quantity_requested: float
    notes: str | None
    requires_tracking: bool


class InventoryDispatchItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_dispatch_item_id: str
    product_id: str
    product_code: str
    product_name: str
    quantity_dispatched: float
    serial_number: str | None
    barcode_value: str | None
    notes: str | None
    requires_tracking: bool
    received_confirmed_by_crm_user_id: str | None
    received_confirmed_by_display_name: str | None = None
    received_confirmed_at: datetime | None
    delivered_confirmed_by_crm_user_id: str | None
    delivered_confirmed_by_display_name: str | None = None
    delivered_confirmed_at: datetime | None
    installed_confirmed_by_crm_user_id: str | None
    installed_confirmed_by_display_name: str | None = None
    installed_confirmed_at: datetime | None


class InventoryDispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_dispatch_id: str
    source_type: str
    source_reference_id: str
    request_id: str | None
    dispatched_by_crm_user_id: str
    dispatched_by_display_name: str | None = None
    warehouse_id: str
    dispatch_notes: str | None
    created_at: datetime
    items: list[InventoryDispatchItemResponse]


class InventoryRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_request_id: str
    source_type: str
    source_reference_id: str
    task_id: str | None
    external_ticket_id: str | None
    request_status: str
    request_reason: str | None
    requested_by_crm_user_id: str
    requested_by_display_name: str | None = None
    reviewed_by_crm_user_id: str | None
    reviewed_by_display_name: str | None = None
    requested_at: datetime
    reviewed_at: datetime | None
    review_notes: str | None
    items: list[InventoryRequestItemResponse]
    dispatches: list[InventoryDispatchResponse]


class InventorySourceFlowResponse(BaseModel):
    source_type: str
    source_reference_id: str
    requests: list[InventoryRequestResponse]
    dispatches: list[InventoryDispatchResponse]