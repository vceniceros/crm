"""Dashboard summary endpoint backed by live database metrics."""

from fastapi import APIRouter, Depends

from crm_backend.api.dependencies import get_authenticated_crm_session, get_dashboard_service
from crm_backend.schemas.common import ErrorResponse
from crm_backend.schemas.dashboard import DashboardSummaryResponse
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_dashboard_summary(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    return dashboard_service.get_dashboard_summary(actor)
