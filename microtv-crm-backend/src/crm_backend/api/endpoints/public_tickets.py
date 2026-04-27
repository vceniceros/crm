"""Public (unauthenticated) ticket satisfaction endpoints.

These endpoints are accessible without a JWT — the token in the URL path
acts as the credential. All token lookups return generic errors to prevent
information leakage.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

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


def _to_satisfaction_detail_response(response) -> SatisfactionResponseDetailResponse:
    return SatisfactionResponseDetailResponse.from_orm_response(response)


async def _parse_submission_payload(
    request: Request,
) -> tuple[SubmitSatisfactionFormRequest, list[UploadFile]]:
    content_type = request.headers.get("content-type", "").lower()
    files: list[UploadFile] = []

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        files = [cast(UploadFile, item) for item in form.getlist("files") if getattr(item, "filename", None)]
        raw_payload = {
            "rating": form.get("rating"),
            "customer_name": form.get("customer_name"),
            "customer_company": form.get("customer_company"),
            "comment": form.get("comment"),
        }
    else:
        raw_payload = await request.json()

    try:
        payload = SubmitSatisfactionFormRequest.model_validate(raw_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return payload, files


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
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionResponseDetailResponse:
    """Submit the client's satisfaction response.

    The token is consumed atomically — only one response per form.
    Media files must be uploaded as multipart fields (optional).
    """
    payload, media_files = await _parse_submission_payload(request)

    response = await sat_service.submit_response(
        raw_token=token,
        rating=payload.rating,
        customer_name=payload.customer_name,
        customer_company=payload.customer_company,
        comment=payload.comment,
        media_files=media_files,
        submitter_ip=_get_client_ip(request),
        submitter_user_agent=request.headers.get("User-Agent"),
    )
    return _to_satisfaction_detail_response(response)


@router.post(
    "/satisfaction/{token}/with-media",
    response_model=SatisfactionResponseDetailResponse,
    responses={404: {"description": "Form not found, expired or already used"}, 409: {"description": "Already responded"}, 422: {"description": "Validation error"}},
    summary="Submit satisfaction response with optional media attachments (multipart)",
)
async def submit_public_satisfaction_form_with_media(
    token: str,
    request: Request,
    rating: Annotated[float, Form(...)],
    customer_name: Annotated[str, Form(...)],
    customer_company: Annotated[str, Form(...)],
    comment: Annotated[str | None, Form()] = None,
    files: list[UploadFile] = File(default=[]),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionResponseDetailResponse:
    """Submit the client's satisfaction response with optional media (multipart/form-data)."""
    try:
        payload = SubmitSatisfactionFormRequest.model_validate(
            {
                "rating": rating,
                "customer_name": customer_name,
                "customer_company": customer_company,
                "comment": comment,
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    response = await sat_service.submit_response(
        raw_token=token,
        rating=payload.rating,
        customer_name=payload.customer_name,
        customer_company=payload.customer_company,
        comment=payload.comment,
        media_files=list(files),
        submitter_ip=_get_client_ip(request),
        submitter_user_agent=request.headers.get("User-Agent"),
    )
    return _to_satisfaction_detail_response(response)
