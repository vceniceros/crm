"""Schemas for CRM settings module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SettingsRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crm_role_id: str
    role_key: str
    role_label: str
    description: str | None
    is_active: bool


class SettingsRoleUpdateRequest(BaseModel):
    role_label: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    is_active: bool = True


class SettingsUserRoleAssignmentResponse(BaseModel):
    crm_user_id: str
    display_name: str | None
    email: str | None
    role_keys: list[str] = Field(default_factory=list)


class SettingsUserRoleAssignmentRequest(BaseModel):
    role_keys: list[str] = Field(default_factory=list)


class SettingsCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: str
    name: str
    category_type: str
    description: str | None
    is_active: bool
    created_at: datetime


class SettingsCategoryWriteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category_type: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    is_active: bool = True


class SettingsPriorityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    priority_id: str
    code: str
    name: str
    order_index: int
    color: str | None
    is_active: bool


class SettingsPriorityWriteRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=80)
    order_index: int = Field(default=0, ge=0)
    color: str | None = Field(default=None, max_length=20)
    is_active: bool = True


class SettingsStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_id: str
    code: str
    name: str
    entity_type: str
    is_final: bool
    order_index: int
    is_active: bool


class SettingsStatusWriteRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=100)
    entity_type: str = Field(..., min_length=1, max_length=30)
    is_final: bool = False
    order_index: int = Field(default=0, ge=0)
    is_active: bool = True


class SettingsTaskTemplateResponse(BaseModel):
    template_id: str
    template_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


class SettingsTaskTemplateUpdateRequest(BaseModel):
    template_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class SettingsSlaRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sla_rule_id: str
    entity_type: str
    priority_code: str
    response_time_minutes: int
    resolution_time_minutes: int
    is_active: bool


class SettingsSlaRuleWriteRequest(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=30)
    priority_code: str = Field(..., min_length=1, max_length=40)
    response_time_minutes: int = Field(..., ge=1)
    resolution_time_minutes: int = Field(..., ge=1)
    is_active: bool = True


class SettingsNotificationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_rule_id: str
    event_code: str
    label: str
    notify_assigned: bool
    notify_roles_json: list[str]
    is_active: bool


class SettingsNotificationRuleWriteRequest(BaseModel):
    event_code: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=180)
    notify_assigned: bool = True
    notify_roles_json: list[str] = Field(default_factory=list)
    is_active: bool = True
