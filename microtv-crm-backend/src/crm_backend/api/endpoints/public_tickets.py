"""Public (unauthenticated) ticket satisfaction endpoints.

These endpoints are accessible without a JWT — the token in the URL path
acts as the credential. All token lookups return generic errors to prevent
information leakage.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from crm_backend.api.dependencies import get_satisfaction_form_service
from crm_backend.schemas.tickets import (
    PublicSatisfactionFormInfoResponse,
    SatisfactionResponseDetailResponse,
    SubmitSatisfactionFormRequest,
)
from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService

router = APIRouter(prefix="/public/tickets", tags=["public-tickets"])


def _get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/satisfaction/{token}",
    response_model=PublicSatisfactionFormInfoResponse,
    responses={404: {"description": "Form not found, expired or already used"}},
    summary="Get public satisfaction form info",
)
def get_public_satisfaction_form(
    token: str,
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> PublicSatisfactionFormInfoResponse:
    """Return minimal safe ticket info for the public satisfaction survey.

    No IDs, no sensitive data exposed. Token is validated server-side.
    """
    form = sat_service.get_public_form_info(token)
    ticket = form.ticket
    client_name: str | None = None
    location_name: str | None = None

    if ticket:
        if ticket.client:
            client_name = getattr(ticket.client, "business_name", None) or getattr(ticket.client, "company_name", None)
        if ticket.location:
            location_name = getattr(ticket.location, "address", None) or getattr(ticket.location, "name", None)

    return PublicSatisfactionFormInfoResponse(
        ticket_number=str(ticket.ticket_number) if ticket else "—",
        client_name=client_name,
        location_name=location_name,
        status_label=form.status_label,
    )


@router.post(
    "/satisfaction/{token}",
    response_model=SatisfactionResponseDetailResponse,
    responses={404: {"description": "Form not found, expired or already used"}, 409: {"description": "Already responded"}, 422: {"description": "Validation error"}},
    summary="Submit a satisfaction response",
)
async def submit_public_satisfaction_form(
    token: str,
    request: Request,
    payload: SubmitSatisfactionFormRequest,
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionResponseDetailResponse:
    """Submit the client's satisfaction response.

    The token is consumed atomically — only one response per form.
    Media files must be uploaded as multipart fields (optional).
    """
    response = await sat_service.submit_response(
        raw_token=token,
        rating=payload.rating,
        comment=payload.comment,
        media_files=[],  # JSON-only endpoint; for multipart use the /multipart variant below
        submitter_ip=_get_client_ip(request),
        submitter_user_agent=request.headers.get("User-Agent"),
    )
    return SatisfactionResponseDetailResponse(
        response_id=response.response_id,
        ticket_id=response.ticket_id,
        rating=response.rating,
        comment=response.comment,
        submitted_at=response.submitted_at,
        media_count=len(response.media or []),
    )


@router.post(
    "/satisfaction/{token}/with-media",
    response_model=SatisfactionResponseDetailResponse,
    responses={404: {"description": "Form not found, expired or already used"}, 409: {"description": "Already responded"}, 422: {"description": "Validation error"}},
    summary="Submit satisfaction response with optional media attachments (multipart)",
)
async def submit_public_satisfaction_form_with_media(
    token: str,
    request: Request,
    rating: float,
    comment: str | None = None,
    files: list[UploadFile] = File(default=[]),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionResponseDetailResponse:
    """Submit the client's satisfaction response with optional media (multipart/form-data)."""
    response = await sat_service.submit_response(
        raw_token=token,
        rating=rating,
        comment=comment,
        media_files=list(files),
        submitter_ip=_get_client_ip(request),
        submitter_user_agent=request.headers.get("User-Agent"),
    )
    return SatisfactionResponseDetailResponse(
        response_id=response.response_id,
        ticket_id=response.ticket_id,
        rating=response.rating,
        comment=response.comment,
        submitted_at=response.submitted_at,
        media_count=len(response.media or []),
    )
