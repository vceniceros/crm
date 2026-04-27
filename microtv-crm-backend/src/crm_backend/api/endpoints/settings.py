"""HTTP endpoints for CRM settings module."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from crm_backend.adapters.auth_service_adapter import AuthManagedUser, AuthServiceAdapter
from crm_backend.api.dependencies import get_auth_service_adapter, get_authenticated_crm_session, get_settings_service
from crm_backend.core.exceptions import ApplicationError
from crm_backend.schemas import ErrorResponse
from crm_backend.schemas.settings import (
    SettingsAuthUserCreateRequest,
    SettingsAuthUserResetPasswordRequest,
    SettingsAuthUserResponse,
    SettingsAuthUserRolesRequest,
    SettingsAuthUserStatusRequest,
    SettingsAuthUserUpdateRequest,
    SettingsCategoryResponse,
    SettingsCategoryWriteRequest,
    SettingsNotificationRuleResponse,
    SettingsNotificationRuleWriteRequest,
    SettingsPriorityResponse,
    SettingsPriorityWriteRequest,
    SettingsRoleResponse,
    SettingsRoleUpdateRequest,
    SettingsSlaRuleResponse,
    SettingsSlaRuleWriteRequest,
    SettingsStatusResponse,
    SettingsStatusWriteRequest,
    SettingsTaskTemplateResponse,
    SettingsTaskTemplateUpdateRequest,
    SettingsUserRoleAssignmentRequest,
    SettingsUserRoleAssignmentResponse,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.settings_service import SettingsService


router = APIRouter(prefix="/settings", tags=["settings"])


def _require_admin(actor: ResolvedCrmSession) -> None:
    if "admin" in actor.role_keys:
        return
    raise ApplicationError("settings_admin_required", "La operación requiere rol administrador.", 403)


def _map_auth_managed_user(user: AuthManagedUser) -> SettingsAuthUserResponse:
    return SettingsAuthUserResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=user.roles,
    )


@router.get("/roles", response_model=list[SettingsRoleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsRoleResponse]:
    return [SettingsRoleResponse.model_validate(role) for role in settings_service.list_roles(actor)]


@router.put("/roles/{role_id}", response_model=SettingsRoleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_role(
    role_id: str,
    payload: SettingsRoleUpdateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsRoleResponse:
    return SettingsRoleResponse.model_validate(settings_service.update_role(actor, role_id, payload))


@router.get("/user-roles", response_model=list[SettingsUserRoleAssignmentResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_user_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsUserRoleAssignmentResponse]:
    users = settings_service.list_user_role_assignments(actor)
    return [
        SettingsUserRoleAssignmentResponse(
            crm_user_id=user.crm_user_id,
            display_name=user.display_name,
            email=user.email,
            role_keys=sorted({assignment.role.role_key for assignment in user.assigned_roles if assignment.role is not None}),
        )
        for user in users
    ]


@router.put("/user-roles/{user_id}", response_model=SettingsUserRoleAssignmentResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def set_user_roles(
    user_id: str,
    payload: SettingsUserRoleAssignmentRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsUserRoleAssignmentResponse:
    user = settings_service.set_user_roles(actor, user_id, payload.role_keys)
    return SettingsUserRoleAssignmentResponse(
        crm_user_id=user.crm_user_id,
        display_name=user.display_name,
        email=user.email,
        role_keys=sorted({assignment.role.role_key for assignment in user.assigned_roles if assignment.role is not None}),
    )


@router.get("/categories", response_model=list[SettingsCategoryResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_categories(
    type: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsCategoryResponse]:
    return [SettingsCategoryResponse.model_validate(item) for item in settings_service.list_categories(actor, type)]


@router.post("/categories", response_model=SettingsCategoryResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_category(
    payload: SettingsCategoryWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsCategoryResponse:
    return SettingsCategoryResponse.model_validate(settings_service.create_category(actor, payload))


@router.put("/categories/{category_id}", response_model=SettingsCategoryResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_category(
    category_id: str,
    payload: SettingsCategoryWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsCategoryResponse:
    return SettingsCategoryResponse.model_validate(settings_service.update_category(actor, category_id, payload))


@router.get("/priorities", response_model=list[SettingsPriorityResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_priorities(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsPriorityResponse]:
    return [SettingsPriorityResponse.model_validate(item) for item in settings_service.list_priorities(actor)]


@router.post("/priorities", response_model=SettingsPriorityResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_priority(
    payload: SettingsPriorityWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsPriorityResponse:
    return SettingsPriorityResponse.model_validate(settings_service.create_priority(actor, payload))


@router.put("/priorities/{priority_id}", response_model=SettingsPriorityResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_priority(
    priority_id: str,
    payload: SettingsPriorityWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsPriorityResponse:
    return SettingsPriorityResponse.model_validate(settings_service.update_priority(actor, priority_id, payload))


@router.get("/statuses", response_model=list[SettingsStatusResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_statuses(
    entity_type: str | None = Query(default=None),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsStatusResponse]:
    return [SettingsStatusResponse.model_validate(item) for item in settings_service.list_statuses(actor, entity_type)]


@router.post("/statuses", response_model=SettingsStatusResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_status(
    payload: SettingsStatusWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsStatusResponse:
    return SettingsStatusResponse.model_validate(settings_service.create_status(actor, payload))


@router.put("/statuses/{status_id}", response_model=SettingsStatusResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_status(
    status_id: str,
    payload: SettingsStatusWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsStatusResponse:
    return SettingsStatusResponse.model_validate(settings_service.update_status(actor, status_id, payload))


@router.get("/task-templates", response_model=list[SettingsTaskTemplateResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_task_templates(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsTaskTemplateResponse]:
    return [
        SettingsTaskTemplateResponse(
            template_id=item.template_id,
            template_name=item.template_name,
            description=item.description,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in settings_service.list_task_templates(actor)
    ]


@router.put("/task-templates/{template_id}", response_model=SettingsTaskTemplateResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_task_template(
    template_id: str,
    payload: SettingsTaskTemplateUpdateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsTaskTemplateResponse:
    updated = settings_service.update_task_template(actor, template_id, payload)
    return SettingsTaskTemplateResponse(
        template_id=updated.template_id,
        template_name=updated.template_name,
        description=updated.description,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.get("/sla", response_model=list[SettingsSlaRuleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_sla_rules(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsSlaRuleResponse]:
    return [SettingsSlaRuleResponse.model_validate(item) for item in settings_service.list_sla_rules(actor)]


@router.post("/sla", response_model=SettingsSlaRuleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_sla_rule(
    payload: SettingsSlaRuleWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsSlaRuleResponse:
    return SettingsSlaRuleResponse.model_validate(settings_service.create_sla_rule(actor, payload))


@router.put("/sla/{rule_id}", response_model=SettingsSlaRuleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_sla_rule(
    rule_id: str,
    payload: SettingsSlaRuleWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsSlaRuleResponse:
    return SettingsSlaRuleResponse.model_validate(settings_service.update_sla_rule(actor, rule_id, payload))


@router.get("/notification-rules", response_model=list[SettingsNotificationRuleResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_notification_rules(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> list[SettingsNotificationRuleResponse]:
    return [SettingsNotificationRuleResponse.model_validate(item) for item in settings_service.list_notification_rules(actor)]


@router.post("/notification-rules", response_model=SettingsNotificationRuleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_notification_rule(
    payload: SettingsNotificationRuleWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsNotificationRuleResponse:
    return SettingsNotificationRuleResponse.model_validate(settings_service.create_notification_rule(actor, payload))


@router.put("/notification-rules/{rule_id}", response_model=SettingsNotificationRuleResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_notification_rule(
    rule_id: str,
    payload: SettingsNotificationRuleWriteRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsNotificationRuleResponse:
    return SettingsNotificationRuleResponse.model_validate(settings_service.update_notification_rule(actor, rule_id, payload))


@router.get("/auth-users", response_model=list[SettingsAuthUserResponse], responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
def list_auth_users(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> list[SettingsAuthUserResponse]:
    _require_admin(actor)
    users = auth_adapter.list_managed_users(actor.auth_result.access_token)
    return [_map_auth_managed_user(user) for user in users]


@router.post("/auth-users", response_model=SettingsAuthUserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_auth_user(
    payload: SettingsAuthUserCreateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> SettingsAuthUserResponse:
    _require_admin(actor)
    created = auth_adapter.create_managed_user(
        access_token=actor.auth_result.access_token,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        is_active=payload.is_active,
        roles=payload.roles,
    )
    return _map_auth_managed_user(created)


@router.put("/auth-users/{user_id}", response_model=SettingsAuthUserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def update_auth_user(
    user_id: str,
    payload: SettingsAuthUserUpdateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> SettingsAuthUserResponse:
    _require_admin(actor)
    updated = auth_adapter.update_managed_user(
        access_token=actor.auth_result.access_token,
        user_id=user_id,
        email=payload.email,
        display_name=payload.display_name,
    )
    return _map_auth_managed_user(updated)


@router.put("/auth-users/{user_id}/status", response_model=SettingsAuthUserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_auth_user_status(
    user_id: str,
    payload: SettingsAuthUserStatusRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> SettingsAuthUserResponse:
    _require_admin(actor)
    updated = auth_adapter.set_managed_user_status(
        access_token=actor.auth_result.access_token,
        user_id=user_id,
        is_active=payload.is_active,
    )
    return _map_auth_managed_user(updated)


@router.put("/auth-users/{user_id}/roles", response_model=SettingsAuthUserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def update_auth_user_roles(
    user_id: str,
    payload: SettingsAuthUserRolesRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> SettingsAuthUserResponse:
    _require_admin(actor)
    updated = auth_adapter.set_managed_user_roles(
        access_token=actor.auth_result.access_token,
        user_id=user_id,
        roles=payload.roles,
    )
    return _map_auth_managed_user(updated)


@router.put("/auth-users/{user_id}/reset-password", response_model=SettingsAuthUserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def reset_auth_user_password(
    user_id: str,
    payload: SettingsAuthUserResetPasswordRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
) -> SettingsAuthUserResponse:
    _require_admin(actor)
    updated = auth_adapter.reset_managed_user_password(
        access_token=actor.auth_result.access_token,
        user_id=user_id,
        new_password=payload.new_password,
    )
    return _map_auth_managed_user(updated)
