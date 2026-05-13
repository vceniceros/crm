from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import TypedDict

from src.db import get_db_session
from src.schemas.crm_admin import (
    CrmAuthUserCreateRequest,
    CrmAuthUserResetPasswordRequest,
    CrmAuthUserResponse,
    CrmAuthUserRolesRequest,
    CrmAuthUserStatusRequest,
    CrmAuthUserUpdateRequest,
)
from src.security.jwt import validate_token
from src.services.crm_identity_service import CrmIdentityService


router = APIRouter(prefix="/v1/crm-admin", tags=["crm-admin"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


class CrmAdminActor(TypedDict):
    user_id: str
    role_keys: set[str]
    is_admin: bool


def get_crm_identity_service(session: Session = Depends(get_db_session)) -> CrmIdentityService:
    return CrmIdentityService(session)


def _normalize_role_keys(claims: dict[str, object]) -> set[str]:
    active_membership = claims.get("active_membership", {})
    if not isinstance(active_membership, dict):
        return set()
    raw_roles = active_membership.get("roles", [])
    if not isinstance(raw_roles, list):
        return set()
    return {str(role).strip().lower() for role in raw_roles if isinstance(role, str) and role.strip()}


def _is_admin_role(role_keys: set[str]) -> bool:
    return "admin" in role_keys or "platform_admin" in role_keys


def _require_crm_admin_or_executive(token: str = Depends(oauth2_scheme)) -> CrmAdminActor:
    try:
        claims = validate_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    role_keys = _normalize_role_keys(claims)
    is_admin = _is_admin_role(role_keys)
    is_executive = "ejecutivo" in role_keys
    if not is_admin and not is_executive:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin or ejecutivo role required.")
    return {
        "user_id": str(claims["sub"]),
        "role_keys": role_keys,
        "is_admin": is_admin,
    }


def _ensure_executive_roles_allowed(actor: CrmAdminActor, roles: list[str]) -> None:
    if actor["is_admin"]:
        return
    normalized_requested_roles = {role.strip().lower() for role in roles if isinstance(role, str) and role.strip()}
    if "admin" in normalized_requested_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ejecutivo cannot assign admin role.")


def _ensure_executive_not_targeting_admin(
    actor: CrmAdminActor,
    crm_identity_service: CrmIdentityService,
    user_id: str,
) -> None:
    if actor["is_admin"]:
        return
    try:
        target_user = crm_identity_service.get_crm_user(user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    target_roles = target_user.get("roles", [])
    if not isinstance(target_roles, list):
        target_roles = []
    normalized_target_roles = {
        role.strip().lower() for role in target_roles if isinstance(role, str) and role.strip()
    }
    if "admin" in normalized_target_roles or "platform_admin" in normalized_target_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ejecutivo cannot manage admin users.")


@router.get("/users", response_model=list[CrmAuthUserResponse])
def list_users(
    _: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> list[CrmAuthUserResponse]:
    return [CrmAuthUserResponse.model_validate(user) for user in crm_identity_service.list_crm_users()]


@router.post("/users", response_model=CrmAuthUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CrmAuthUserCreateRequest,
    actor: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    _ensure_executive_roles_allowed(actor, payload.roles)
    try:
        user = crm_identity_service.create_crm_user(
            email=str(payload.email),
            display_name=payload.display_name,
            password=payload.password,
            is_active=payload.is_active,
            roles=payload.roles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))


@router.put("/users/{user_id}", response_model=CrmAuthUserResponse)
def update_user(
    user_id: str,
    payload: CrmAuthUserUpdateRequest,
    actor: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    _ensure_executive_not_targeting_admin(actor, crm_identity_service, user_id)
    try:
        user = crm_identity_service.update_crm_user(
            user_id=user_id,
            email=str(payload.email),
            display_name=payload.display_name,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "User not found." else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))


@router.put("/users/{user_id}/status", response_model=CrmAuthUserResponse)
def set_user_status(
    user_id: str,
    payload: CrmAuthUserStatusRequest,
    actor: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    _ensure_executive_not_targeting_admin(actor, crm_identity_service, user_id)
    try:
        user = crm_identity_service.set_user_active(user_id=user_id, is_active=payload.is_active)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))


@router.put("/users/{user_id}/roles", response_model=CrmAuthUserResponse)
def set_user_roles(
    user_id: str,
    payload: CrmAuthUserRolesRequest,
    actor: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    _ensure_executive_not_targeting_admin(actor, crm_identity_service, user_id)
    _ensure_executive_roles_allowed(actor, payload.roles)
    try:
        user = crm_identity_service.set_user_roles(user_id=user_id, roles=payload.roles)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "User not found." else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))


@router.put("/users/{user_id}/reset-password", response_model=CrmAuthUserResponse)
def reset_user_password(
    user_id: str,
    payload: CrmAuthUserResetPasswordRequest,
    actor: CrmAdminActor = Depends(_require_crm_admin_or_executive),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    _ensure_executive_not_targeting_admin(actor, crm_identity_service, user_id)
    try:
        user = crm_identity_service.reset_user_password(user_id=user_id, new_password=payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))
