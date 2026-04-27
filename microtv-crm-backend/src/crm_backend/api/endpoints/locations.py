"""HTTP endpoints for reusable real locations."""

from fastapi import APIRouter, Depends, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_location_application_service
from crm_backend.schemas import CreateLocationRequest, ErrorResponse, LocationResponse
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.location_service import CreateLocationCommand, LocationApplicationService


router = APIRouter(prefix="/locations", tags=["locations"])


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def create_location(
    payload: CreateLocationRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    location_service: LocationApplicationService = Depends(get_location_application_service),
) -> LocationResponse:
    location = location_service.create_location(
        actor,
        CreateLocationCommand(
            latitude=payload.latitude,
            longitude=payload.longitude,
            address_label=payload.address_label,
            formatted_address=payload.formatted_address,
        ),
    )
    return LocationResponse.model_validate(location)
