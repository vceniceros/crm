"""Schemas for asset management."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AssetFieldType = Literal["string", "number"]


class CreateAssetCategoryFieldRequest(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=120)
    field_type: AssetFieldType
    is_required: bool = False
    order_index: int = 0


class CreateAssetCategoryRequest(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    fields: list[CreateAssetCategoryFieldRequest] = Field(default_factory=list)


class AssetFieldValueRequest(BaseModel):
    field_id: str
    value: str = ""


class CreateAssetRequest(BaseModel):
    category_id: str
    client_id: str
    asset_name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None
    parent_asset_id: str | None = None
    field_values: list[AssetFieldValueRequest] = Field(default_factory=list)


class UpdateAssetRequest(BaseModel):
    asset_name: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None
    parent_asset_id: str | None = None
    field_values: list[AssetFieldValueRequest] | None = None


class LinkAssetRequest(BaseModel):
    asset_id: str


class AssetCategoryFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    field_name: str
    field_type: str
    is_required: bool
    order_index: int


class AssetCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_category_id: str
    category_name: str
    description: str | None
    is_active: bool
    fields: list[AssetCategoryFieldResponse] = Field(default_factory=list)


class AssetFieldValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    field_name: str
    field_type: str
    raw_value: str


class AssetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    asset_name: str
    category_name: str
    client_name: str
    parent_asset_id: str | None
    parent_asset_name: str | None
    created_by_crm_user_id: str


class AssetResponse(AssetSummaryResponse):
    category_id: str
    client_id: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    field_values: list[AssetFieldValueResponse] = Field(default_factory=list)
