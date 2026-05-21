"""HTTP endpoints for the ticket module."""

from datetime import UTC, datetime
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from crm_backend.api.dependencies import (
    get_authenticated_crm_session,
    get_satisfaction_form_service,
    get_ticket_application_service,
    get_ticket_export_service,
)
from crm_backend.core.exceptions import InvalidTaskAttachmentError
from crm_backend.schemas import (
    ApproveTicketRequest,
    AssignTicketRequest,
    CloseTicketRequest,
    CreateTicketCommentRequest,
    CreateTicketRequest,
    ErrorResponse,
    RejectTicketApprovalRequest,
    ReopenTicketRequest,
    TicketAttachmentResponse,
    TicketDetailResponse,
    TicketRoleOptionResponse,
    TicketSummaryResponse,
    UpdateTicketStatusRequest,
)
from crm_backend.schemas.tickets import (
    GenerateSatisfactionFormResponse,
    RegisterArrivalRequest,
    SatisfactionFormStatusResponse,
    SatisfactionResponseDetailResponse,
)
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.satisfaction_form_service import PublicSatisfactionFormService
from crm_backend.services.ticket_export_service import TicketExportService
from crm_backend.services.ticket_service import TicketApplicationService


router = APIRouter(prefix="/tickets", tags=["tickets"])
_logger = logging.getLogger(__name__)


def _safe_ticket_summary_list(items: list[object]) -> list[TicketSummaryResponse]:
    response: list[TicketSummaryResponse] = []
    for index, item in enumerate(items):
        try:
            response.append(TicketSummaryResponse.model_validate(item))
        except Exception:
            _logger.exception("Failed to serialize ticket summary item at index %s", index)
    return response


def _to_ticket_detail_response(
    *,
    actor: ResolvedCrmSession,
    ticket_service: TicketApplicationService,
    ticket,
) -> TicketDetailResponse:
    setattr(ticket, "has_arrival_registered", ticket_service.has_arrival_registered(ticket))
    setattr(ticket, "can_register_arrival", ticket_service.can_register_arrival(actor, ticket))
    return TicketDetailResponse.model_validate(ticket)


def _build_export_response(ticket, zip_bytes: bytes) -> StreamingResponse:
    ticket_number = ticket.ticket_number or ticket.ticket_id
    date_label = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"ticket_{ticket_number}_{date_label}.zip"
    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_ticket_survey_response(
    *,
    actor: ResolvedCrmSession,
    ticket_id: str,
    ticket_service: TicketApplicationService,
    sat_service: PublicSatisfactionFormService,
) -> GenerateSatisfactionFormResponse:
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    form, raw_token = sat_service.generate_form(actor, ticket)
    return GenerateSatisfactionFormResponse(
        form_id=form.form_id,
        ticket_id=form.ticket_id,
        public_link_token=raw_token,
        survey_path=f"/survey/{raw_token}",
        expires_at=form.expires_at,
        status_label=form.status_label,
    )


@router.get(
    "/roles",
    response_model=list[TicketRoleOptionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_assignable_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketRoleOptionResponse]:
    try:
        roles = ticket_service.list_assignable_roles(actor)
        response: list[TicketRoleOptionResponse] = []
        for role in roles:
            role_id = str(getattr(role, "crm_role_id", "") or "").strip()
            role_key = str(getattr(role, "role_key", "") or "").strip()
            role_label = str(getattr(role, "role_label", "") or "").strip()
            if not role_id or not role_key or not role_label:
                continue
            response.append(
                TicketRoleOptionResponse(
                    crm_role_id=role_id,
                    role_key=role_key,
                    role_label=role_label,
                )
            )
        return response
    except Exception:
        _logger.exception("Failed to serialize assignable roles for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
        return []


@router.post(
    "",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_ticket(
    payload: CreateTicketRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.create_ticket(actor, payload)
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.get(
    "/assigned/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_my_assigned_tickets(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return _safe_ticket_summary_list(ticket_service.list_tickets_assigned_to_actor(actor))


@router.get(
    "/unassigned/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_unassigned_tickets_for_my_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return _safe_ticket_summary_list(ticket_service.list_unassigned_tickets_for_actor(actor))


@router.get(
    "/tracking/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_tracking_tickets_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return _safe_ticket_summary_list(ticket_service.list_tracking_tickets_for_actor(actor))


@router.get(
    "/history/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_closed_tickets_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return _safe_ticket_summary_list(ticket_service.list_closed_tickets_for_actor(actor))


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_ticket_detail(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/assignment",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def assign_ticket(
    ticket_id: str,
    payload: AssignTicketRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.assign_ticket(
        actor,
        ticket_id,
        payload.assigned_role_id,
        payload.assigned_user_id,
        payload.notes,
        payload.collaborator_user_ids,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def add_ticket_comment(
    ticket_id: str,
    payload: CreateTicketCommentRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.add_comment(
        actor,
        ticket_id,
        body=payload.body,
        location_id=payload.location_id,
        attachment_ids=payload.attachment_ids,
        mentioned_user_ids=payload.mentioned_user_ids,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.post(
    "/{ticket_id}/comments/{comment_id}/mark-as-solution",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def mark_comment_as_solution(
    ticket_id: str,
    comment_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.mark_comment_as_solution(actor, ticket_id, comment_id)
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_ticket_status(
    ticket_id: str,
    payload: UpdateTicketStatusRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.update_status(
        actor,
        ticket_id,
        to_status=payload.to_status,
        comment=payload.comment,
        attachment_ids=payload.attachment_ids,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/approve",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def approve_ticket(
    ticket_id: str,
    payload: ApproveTicketRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.approve_ticket(actor, ticket_id, payload.comment)
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/reject",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_ticket_approval(
    ticket_id: str,
    payload: RejectTicketApprovalRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.reject_ticket_approval(actor, ticket_id, payload.comment)
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/close",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def close_ticket(
    ticket_id: str,
    payload: CloseTicketRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.close_ticket(
        actor,
        ticket_id,
        comment=payload.comment,
        attachment_ids=payload.attachment_ids,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.patch(
    "/{ticket_id}/reopen",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reopen_ticket(
    ticket_id: str,
    payload: ReopenTicketRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.reopen_ticket(
        actor,
        ticket_id,
        comment=payload.comment,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


@router.post(
    "/{ticket_id}/attachments",
    response_model=list[TicketAttachmentResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_ticket_attachments(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile] | None, File(alias="files")] = None,
    file: Annotated[UploadFile | None, File(alias="file")] = None,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketAttachmentResponse]:
    resolved_files = list(files or [])
    if file is not None:
        resolved_files.append(file)
    if not resolved_files:
        raise InvalidTaskAttachmentError(
            "No se recibieron archivos en el formulario multipart. Usá el campo 'files' (o 'file' para uno solo)."
        )

    return [
        TicketAttachmentResponse.model_validate(item)
        for item in await ticket_service.upload_ticket_attachments(actor, ticket_id, resolved_files, background_tasks)
    ]


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def delete_ticket_attachment(
    attachment_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> Response:
    ticket_service.delete_ticket_attachment(actor, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Arrival registration (US-1)
# ---------------------------------------------------------------------------


@router.post(
    "/{ticket_id}/arrival",
    response_model=TicketDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def register_arrival(
    ticket_id: str,
    payload: RegisterArrivalRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> TicketDetailResponse:
    ticket = ticket_service.register_arrival(
        actor,
        ticket_id,
        body=payload.body,
        attachment_ids=payload.attachment_ids,
    )
    return _to_ticket_detail_response(actor=actor, ticket_service=ticket_service, ticket=ticket)


# ---------------------------------------------------------------------------
# Satisfaction form (US-2)
# ---------------------------------------------------------------------------


@router.post(
    "/{ticket_id}/generate-survey",
    response_model=GenerateSatisfactionFormResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def generate_ticket_survey(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> GenerateSatisfactionFormResponse:
    return _generate_ticket_survey_response(
        actor=actor,
        ticket_id=ticket_id,
        ticket_service=ticket_service,
        sat_service=sat_service,
    )


@router.post(
    "/{ticket_id}/satisfaction-form",
    response_model=GenerateSatisfactionFormResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def generate_satisfaction_form(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> GenerateSatisfactionFormResponse:
    return _generate_ticket_survey_response(
        actor=actor,
        ticket_id=ticket_id,
        ticket_service=ticket_service,
        sat_service=sat_service,
    )


@router.post(
    "/{ticket_id}/satisfaction-form/revoke",
    response_model=SatisfactionFormStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def revoke_satisfaction_form(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionFormStatusResponse:
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    form = sat_service.revoke_form(actor, ticket)
    return SatisfactionFormStatusResponse.from_orm_form(form)


@router.get(
    "/{ticket_id}/satisfaction-form/status",
    response_model=SatisfactionFormStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_satisfaction_form_status(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionFormStatusResponse:
    from crm_backend.core.exceptions import SatisfactionFormNotFoundError  # noqa: PLC0415
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    form = sat_service.get_form_status(actor, ticket)
    if form is None:
        raise SatisfactionFormNotFoundError()
    return SatisfactionFormStatusResponse.from_orm_form(form)


@router.get(
    "/{ticket_id}/satisfaction-form/response",
    response_model=SatisfactionResponseDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_satisfaction_response(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    sat_service: PublicSatisfactionFormService = Depends(get_satisfaction_form_service),
) -> SatisfactionResponseDetailResponse:
    from crm_backend.core.exceptions import SatisfactionFormNotFoundError  # noqa: PLC0415
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    resp = sat_service.get_response_for_ticket(actor, ticket)
    if resp is None:
        raise SatisfactionFormNotFoundError()
    return SatisfactionResponseDetailResponse.from_orm_response(resp)


# ---------------------------------------------------------------------------
# Ticket history export
# ---------------------------------------------------------------------------


@router.get(
    "/{ticket_id}/export",
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP archive with PDF + multimedia"},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def export_ticket_history(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    export_service: TicketExportService = Depends(get_ticket_export_service),
) -> StreamingResponse:
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    zip_bytes = export_service.export_development_zip(actor, ticket)
    return _build_export_response(ticket, zip_bytes)


@router.get(
    "/{ticket_id}/export-development",
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP archive with PDF + multimedia"},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def export_ticket_development(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
    export_service: TicketExportService = Depends(get_ticket_export_service),
) -> StreamingResponse:
    ticket = ticket_service.get_ticket_detail(actor, ticket_id)
    zip_bytes = export_service.export_development_zip(actor, ticket)
    return _build_export_response(ticket, zip_bytes)
