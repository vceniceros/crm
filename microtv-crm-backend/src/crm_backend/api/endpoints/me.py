"""HTTP endpoints for authenticated user self-management."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from crm_backend.adapters.auth_service_adapter import AuthServiceAdapter
from crm_backend.api.dependencies import (
    get_auth_service_adapter,
    get_authenticated_crm_session,
    get_settings,
)
from crm_backend.core.config import Settings
from crm_backend.core.exceptions import ApplicationError
from crm_backend.db import get_db_session
from crm_backend.schemas import ErrorResponse
from crm_backend.schemas.me import MePatchRequest, MeResponse
from crm_backend.services.auth_service import ResolvedCrmSession


router = APIRouter(prefix="/me", tags=["me"])


def _normalize_role_key(role_key: str | None) -> str | None:
    if not isinstance(role_key, str):
        return None
    normalized = role_key.strip()
    if normalized == "admin_crm":
        return "admin"
    if normalized == "tecnico_campo":
        return "tecnico"
    if normalized == "encargado_deposito":
        return "deposito"
    return normalized or None


def _resolved_roles(actor: ResolvedCrmSession) -> list[str]:
    roles = {
        _normalize_role_key(assignment.role.role_key)
        for assignment in actor.crm_user.assigned_roles
        if assignment.role is not None and assignment.role.is_active
    }
    return sorted(role for role in roles if role)


def _build_me_response(actor: ResolvedCrmSession) -> MeResponse:
    return MeResponse(
        display_name=actor.crm_user.display_name,
        email=actor.crm_user.email,
        avatar_url=actor.crm_user.avatar_url,
        roles=_resolved_roles(actor),
    )


@router.get(
    "",
    response_model=MeResponse,
    responses={401: {"model": ErrorResponse}},
)
def get_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
) -> MeResponse:
    return _build_me_response(actor)


@router.patch(
    "",
    response_model=MeResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def patch_me(
    payload: MePatchRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
    db: Session = Depends(get_db_session),
) -> MeResponse:
    next_display_name = payload.display_name if payload.display_name is not None else actor.crm_user.display_name
    next_email = payload.email if payload.email is not None else actor.crm_user.email

    if not next_email:
        next_email = actor.auth_result.email
    if not next_display_name:
        next_display_name = actor.crm_user.display_name or actor.auth_result.display_name or actor.crm_user.auth_user_id

    if not next_email:
        raise ApplicationError("me_email_required", "No se pudo resolver un email válido para actualizar el perfil.", 422)

    auth_user = auth_adapter.update_managed_user(
        access_token=actor.auth_result.access_token,
        user_id=actor.auth_result.auth_user_id,
        email=next_email,
        display_name=next_display_name,
    )

    actor.crm_user.email = auth_user.email
    actor.crm_user.display_name = auth_user.display_name
    db.add(actor.crm_user)
    db.commit()
    db.refresh(actor.crm_user)
    return _build_me_response(actor)


@router.post(
    "/avatar",
    response_model=MeResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_avatar(
    file: UploadFile = File(...),
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
) -> MeResponse:
    content_type = (file.content_type or "").strip().lower()
    if not content_type.startswith("image/"):
        raise ApplicationError("me_avatar_invalid_type", "La foto de perfil debe ser una imagen válida.", 422)

    suffix = Path(file.filename or "").suffix.lower()
    mime_to_suffix = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    resolved_suffix = suffix if suffix in allowed_suffixes else mime_to_suffix.get(content_type, ".jpg")

    payload = await file.read()
    if not payload:
        raise ApplicationError("me_avatar_empty", "El archivo de avatar está vacío.", 422)
    if len(payload) > 5 * 1024 * 1024:
        raise ApplicationError("me_avatar_too_large", "El avatar supera el tamaño máximo permitido de 5 MB.", 422)

    avatar_dir = settings.public_avatars_dir
    avatar_dir.mkdir(parents=True, exist_ok=True)

    # Keep only one avatar per CRM user to avoid stale files with old extensions.
    for existing_avatar in avatar_dir.glob(f"{actor.crm_user.crm_user_id}.*"):
        try:
            existing_avatar.unlink(missing_ok=True)
        except OSError:
            continue

    avatar_filename = f"{actor.crm_user.crm_user_id}{resolved_suffix}"
    avatar_path = avatar_dir / avatar_filename
    avatar_path.write_bytes(payload)

    actor.crm_user.avatar_url = f"/avatars/{avatar_filename}"
    db.add(actor.crm_user)
    db.commit()
    db.refresh(actor.crm_user)
    return _build_me_response(actor)


@router.post(
    "/request-password-reset",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def request_password_reset(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    auth_adapter: AuthServiceAdapter = Depends(get_auth_service_adapter),
    settings: Settings = Depends(get_settings),
) -> Response:
    email = actor.crm_user.email or actor.auth_result.email
    if not email:
        raise ApplicationError("me_email_required", "No se pudo resolver el email del usuario autenticado.", 422)

    auth_adapter.request_password_reset(
        email=email,
        recaptcha_token=settings.auth_service_recaptcha_token,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
