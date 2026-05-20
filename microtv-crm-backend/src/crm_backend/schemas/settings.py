"""Schemas for CRM settings module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class SettingsAuthUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)


class SettingsAuthUserCreateRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    display_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8)
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)


class SettingsAuthUserUpdateRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    display_name: str = Field(..., min_length=2, max_length=120)


class SettingsAuthUserStatusRequest(BaseModel):
    is_active: bool


class SettingsAuthUserRolesRequest(BaseModel):
    roles: list[str] = Field(default_factory=list)


class SettingsAuthUserResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


class SettingsCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: str
    name: str
    category_type: str
    description: str | None
    is_active: bool
    is_system: bool = False
    default_role_id: str | None = None
    default_role_key: str | None = None
    default_role_label: str | None = None
    allows_scheduling: bool = False
    schedule_period_type: str | None = None
    schedule_interval_weeks: int | None = None
    schedule_weekdays_json: list[int] = Field(default_factory=list)
    schedule_start_date: date | None = None
    schedule_end_date: date | None = None
    created_at: datetime

    @classmethod
    def from_orm_with_role(cls, obj: object) -> "SettingsCategoryResponse":
        instance = cls.model_validate(obj)
        role = getattr(obj, "default_role", None)
        if role is not None:
            instance.default_role_key = getattr(role, "role_key", None)
            instance.default_role_label = getattr(role, "role_label", None)
        return instance


class SettingsCategoryWriteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category_type: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    is_active: bool = True
    default_role_id: str | None = None
    allows_scheduling: bool = False
    schedule_period_type: str | None = Field(default=None, pattern=r"^(daily|weekly|biweekly|monthly|custom)$")
    schedule_interval_weeks: int | None = Field(default=None, ge=1, le=52)
    schedule_weekdays_json: list[int] = Field(default_factory=list)
    schedule_start_date: date | None = None
    schedule_end_date: date | None = None

    @field_validator("schedule_weekdays_json")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        weekdays: set[int] = set()
        for day in value:
            try:
                normalized = int(day)
            except (TypeError, ValueError):
                continue
            if 1 <= normalized <= 7:
                weekdays.add(normalized)
        return sorted(weekdays)


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
