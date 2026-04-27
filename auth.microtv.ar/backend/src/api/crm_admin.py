from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

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


def get_crm_identity_service(session: Session = Depends(get_db_session)) -> CrmIdentityService:
    return CrmIdentityService(session)


def _require_crm_admin(token: str = Depends(oauth2_scheme)) -> str:
    try:
        claims = validate_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    active_membership = claims.get("active_membership", {})
    roles = active_membership.get("roles", [])
    if "admin" not in roles and "platform_admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required.")
    return str(claims["sub"])


@router.get("/users", response_model=list[CrmAuthUserResponse])
def list_users(
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> list[CrmAuthUserResponse]:
    return [CrmAuthUserResponse.model_validate(user) for user in crm_identity_service.list_crm_users()]


@router.post("/users", response_model=CrmAuthUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CrmAuthUserCreateRequest,
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
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
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
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
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    try:
        user = crm_identity_service.set_user_active(user_id=user_id, is_active=payload.is_active)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))


@router.put("/users/{user_id}/roles", response_model=CrmAuthUserResponse)
def set_user_roles(
    user_id: str,
    payload: CrmAuthUserRolesRequest,
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
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
    _: str = Depends(_require_crm_admin),
    crm_identity_service: CrmIdentityService = Depends(get_crm_identity_service),
) -> CrmAuthUserResponse:
    try:
        user = crm_identity_service.reset_user_password(user_id=user_id, new_password=payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CrmAuthUserResponse.model_validate(crm_identity_service.render_user(user))
