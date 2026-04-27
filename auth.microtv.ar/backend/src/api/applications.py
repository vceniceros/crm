"""
Public-facing endpoints for company accreditation applications.

POST /v1/applications                — create (draft), no auth required
GET  /v1/applications/{id}           — status check, no auth required
POST /v1/applications/{id}/submit    — AFIP validation + draft→fiscal_verified
PATCH /v1/applications/{id}          — correct + reopen a rejected application
POST /v1/applications/{id}/mp-verified — callback from pay.microtv.ar after MP OAuth
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from src.config import settings
from src.db import get_db_session
from src.schemas.application import (
    ApplicationResponse,
    CreateApplicationRequest,
    MpVerifiedCallbackRequest,
    UpdateApplicationRequest,
)
from src.services.application_service import ApplicationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/applications", tags=["applications"])


def get_application_service(session: Session = Depends(get_db_session)) -> ApplicationService:
    return ApplicationService(session)


def _require_service_token(x_service_token: str = Header(...)) -> None:
    """Validates the shared secret used by pay.microtv.ar for internal callbacks."""
    if x_service_token != settings.service_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token.",
        )


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: CreateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Create a new accreditation application (starts in draft)."""
    app = service.create(payload)
    return ApplicationResponse.model_validate(app)


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Return current status of an application. No auth — applicant uses application_id as ref."""
    try:
        app = service.get(application_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApplicationResponse.model_validate(app)


@router.post("/{application_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    application_id: str,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """
    Submit a draft application for AFIP fiscal validation.
    On success: transitions to fiscal_verified.
    On AFIP rejection: raises 422 with the reason (applicant can correct and resubmit).
    On AFIP unreachable: raises 503.
    """
    try:
        app = await service.submit(application_id)
    except ValueError as exc:
        msg = str(exc)
        # AFIP connectivity issues → 503 so applicant knows to retry
        if "timed out" in msg or "conectar" in msg or "inesperada" in msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
            ) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg) from exc
    return ApplicationResponse.model_validate(app)


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    payload: UpdateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """
    Update a rejected application with corrections and move it back to draft.
    Only allowed when status == rejected.
    """
    try:
        app = service.update_and_reopen(application_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ApplicationResponse.model_validate(app)


@router.post("/{application_id}/mp-verified", response_model=ApplicationResponse)
def mp_verified_callback(
    application_id: str,
    payload: MpVerifiedCallbackRequest,
    _: None = Depends(_require_service_token),
    service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """
    Internal callback from pay.microtv.ar after the applicant completes MP OAuth.
    Transitions: fiscal_verified → mp_verified → under_review (automatic).
    Requires X-Service-Token header.
    """
    try:
        app = service.mark_mp_verified(application_id, payload.mp_account_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ApplicationResponse.model_validate(app)
