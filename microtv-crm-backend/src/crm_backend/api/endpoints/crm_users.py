"""HTTP endpoints for CRM user lookup."""

from fastapi import APIRouter, Depends, Query

from crm_backend.api.dependencies import get_authenticated_crm_session, get_crm_user_repository
from crm_backend.repositories import CrmUserRepository
from crm_backend.schemas import CrmUserOptionResponse, ErrorResponse
from crm_backend.services.auth_service import ResolvedCrmSession


router = APIRouter(prefix="/crm-users", tags=["crm-users"])


@router.get(
    "",
    response_model=list[CrmUserOptionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_crm_users(
    role_key: str = Query(..., min_length=1),
    _: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    repository: CrmUserRepository = Depends(get_crm_user_repository),
) -> list[CrmUserOptionResponse]:
    return [CrmUserOptionResponse.model_validate(item) for item in repository.list_active_by_role_key(role_key)]