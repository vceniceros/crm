"""HTTP endpoints for the ticket module."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_ticket_application_service
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
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.ticket_service import TicketApplicationService


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get(
    "/roles",
    response_model=list[TicketRoleOptionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_assignable_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketRoleOptionResponse]:
    roles = ticket_service.list_assignable_roles(actor)
    return [
        TicketRoleOptionResponse(
            crm_role_id=role.crm_role_id,
            role_key=role.role_key,
            role_label=role.role_label,
        )
        for role in roles
    ]


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
    return TicketDetailResponse.model_validate(ticket_service.create_ticket(actor, payload))


@router.get(
    "/assigned/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_my_assigned_tickets(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return [TicketSummaryResponse.model_validate(item) for item in ticket_service.list_tickets_assigned_to_actor(actor)]


@router.get(
    "/unassigned/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_unassigned_tickets_for_my_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return [TicketSummaryResponse.model_validate(item) for item in ticket_service.list_unassigned_tickets_for_actor(actor)]


@router.get(
    "/tracking/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_tracking_tickets_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return [TicketSummaryResponse.model_validate(item) for item in ticket_service.list_tracking_tickets_for_actor(actor)]


@router.get(
    "/history/me",
    response_model=list[TicketSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_closed_tickets_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketSummaryResponse]:
    return [TicketSummaryResponse.model_validate(item) for item in ticket_service.list_closed_tickets_for_actor(actor)]


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
    return TicketDetailResponse.model_validate(ticket_service.get_ticket_detail(actor, ticket_id))


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
    return TicketDetailResponse.model_validate(
        ticket_service.assign_ticket(
            actor,
            ticket_id,
            payload.assigned_role_id,
            payload.assigned_user_id,
            payload.notes,
        )
    )


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
    return TicketDetailResponse.model_validate(
        ticket_service.add_comment(
            actor,
            ticket_id,
            body=payload.body,
            location_id=payload.location_id,
            attachment_ids=payload.attachment_ids,
        )
    )


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
    return TicketDetailResponse.model_validate(
        ticket_service.update_status(
            actor,
            ticket_id,
            to_status=payload.to_status,
            comment=payload.comment,
            attachment_ids=payload.attachment_ids,
        )
    )


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
    return TicketDetailResponse.model_validate(ticket_service.approve_ticket(actor, ticket_id, payload.comment))


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
    return TicketDetailResponse.model_validate(ticket_service.reject_ticket_approval(actor, ticket_id, payload.comment))


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
    return TicketDetailResponse.model_validate(
        ticket_service.close_ticket(
            actor,
            ticket_id,
            comment=payload.comment,
            attachment_ids=payload.attachment_ids,
        )
    )


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
    return TicketDetailResponse.model_validate(
        ticket_service.reopen_ticket(
            actor,
            ticket_id,
            comment=payload.comment,
        )
    )


@router.post(
    "/{ticket_id}/attachments",
    response_model=list[TicketAttachmentResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_ticket_attachments(
    ticket_id: str,
    files: Annotated[list[UploadFile], File(...)],
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    ticket_service: TicketApplicationService = Depends(get_ticket_application_service),
) -> list[TicketAttachmentResponse]:
    return [
        TicketAttachmentResponse.model_validate(item)
        for item in await ticket_service.upload_ticket_attachments(actor, ticket_id, files)
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
