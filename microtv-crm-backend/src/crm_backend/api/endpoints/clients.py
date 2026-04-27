"""HTTP endpoints for real CRM client management."""

from fastapi import APIRouter, Depends, Response, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_client_application_service
from crm_backend.schemas import ClientSummaryResponse, CreateClientRequest, ErrorResponse, UpdateClientRequest
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.client_service import (
    ClientApplicationService,
    ClientLocationCommand,
    ClientView,
    CreateClientCommand,
    UpdateClientCommand,
)


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get(
    "",
    response_model=list[ClientSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_clients(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    client_service: ClientApplicationService = Depends(get_client_application_service),
) -> list[ClientSummaryResponse]:
    return [_to_client_response(item) for item in client_service.list_clients(actor)]


@router.get(
    "/{client_id}",
    response_model=ClientSummaryResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_client(
    client_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    client_service: ClientApplicationService = Depends(get_client_application_service),
) -> ClientSummaryResponse:
    return _to_client_response(client_service.get_client(actor, client_id))


@router.post(
    "",
    response_model=ClientSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_client(
    payload: CreateClientRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    client_service: ClientApplicationService = Depends(get_client_application_service),
) -> ClientSummaryResponse:
    client = client_service.create_client(
        actor,
        CreateClientCommand(
            business_name=payload.business_name,
            tax_id=payload.tax_id,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            location=_to_location_command(payload.location),
        ),
    )
    return _to_client_response(client)


@router.put(
    "/{client_id}",
    response_model=ClientSummaryResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_client(
    client_id: str,
    payload: UpdateClientRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    client_service: ClientApplicationService = Depends(get_client_application_service),
) -> ClientSummaryResponse:
    client = client_service.update_client(
        actor,
        client_id,
        UpdateClientCommand(
            business_name=payload.business_name,
            tax_id=payload.tax_id,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            is_active=payload.is_active,
            location=_to_location_command(payload.location),
        ),
    )
    return _to_client_response(client)


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_client(
    client_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    client_service: ClientApplicationService = Depends(get_client_application_service),
) -> Response:
    client_service.delete_client(actor, client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_location_command(payload: object) -> ClientLocationCommand | None:
    if payload is None:
        return None
    return ClientLocationCommand(
        latitude=payload.latitude,
        longitude=payload.longitude,
        address_label=payload.address_label,
        formatted_address=payload.formatted_address,
    )


def _to_client_response(client: ClientView) -> ClientSummaryResponse:
    return ClientSummaryResponse.model_validate(client)