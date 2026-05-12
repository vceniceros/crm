"""Schemas for permissions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RolePermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_permission_id: str
    role_key: str
    permission_code: str
    is_granted: bool


class UserPermissionOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_permission_id: str
    crm_user_id: str
    permission_code: str
    is_granted: bool
    granted_by_crm_user_id: str | None


class PermissionUpdateRequest(BaseModel):
    is_granted: bool


class EffectivePermissionsResponse(BaseModel):
    permissions: dict[str, bool]
