"""HTTP endpoints for asset management."""

from fastapi import APIRouter, Depends, Response, status

from crm_backend.api.dependencies import get_asset_application_service, get_authenticated_crm_session
from crm_backend.schemas import (
    AssetCategoryFieldResponse,
    AssetCategoryResponse,
    AssetResponse,
    AssetSummaryResponse,
    CreateAssetCategoryRequest,
    CreateAssetRequest,
    ErrorResponse,
    LinkAssetRequest,
    TaskSummaryResponse,
    TicketSummaryResponse,
    UpdateAssetRequest,
)
from crm_backend.services.assets import AssetApplicationService
from crm_backend.services.auth_service import ResolvedCrmSession


router = APIRouter(tags=["assets"])


@router.get("/asset-categories", response_model=list[AssetCategoryResponse], responses={401: {"model": ErrorResponse}})
def list_asset_categories(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[AssetCategoryResponse]:
    return [AssetCategoryResponse.model_validate(item) for item in asset_service.list_categories(actor)]


@router.post(
    "/asset-categories",
    response_model=AssetCategoryResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_asset_category(
    payload: CreateAssetCategoryRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> AssetCategoryResponse:
    return AssetCategoryResponse.model_validate(asset_service.create_category(actor, payload))


@router.get("/asset-categories/{category_id}/fields", response_model=list[AssetCategoryFieldResponse])
def list_asset_category_fields(
    category_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[AssetCategoryFieldResponse]:
    return [AssetCategoryFieldResponse.model_validate(item) for item in asset_service.get_category(actor, category_id).fields]


@router.get("/assets", response_model=list[AssetSummaryResponse], responses={401: {"model": ErrorResponse}})
def list_assets(
    client_id: str | None = None,
    category_id: str | None = None,
    search: str | None = None,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[AssetSummaryResponse]:
    return [AssetSummaryResponse.model_validate(item) for item in asset_service.list_assets(actor, client_id, category_id, search)]


@router.post(
    "/assets",
    response_model=AssetResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_asset(
    payload: CreateAssetRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> AssetResponse:
    return AssetResponse.model_validate(asset_service.create_asset(actor, payload))


@router.get("/assets/{asset_id}", response_model=AssetResponse, responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_asset(
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> AssetResponse:
    return AssetResponse.model_validate(asset_service.get_asset(actor, asset_id))


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: str,
    payload: UpdateAssetRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> AssetResponse:
    return AssetResponse.model_validate(asset_service.update_asset(actor, asset_id, payload))


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_asset(
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> Response:
    asset_service.delete_asset(actor, asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/assets/{asset_id}/tickets", response_model=list[TicketSummaryResponse])
def list_tickets_for_asset(
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[TicketSummaryResponse]:
    return [TicketSummaryResponse.model_validate(item) for item in asset_service.list_tickets_for_asset(actor, asset_id)]


@router.get("/assets/{asset_id}/tasks", response_model=list[TaskSummaryResponse])
def list_tasks_for_asset(
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[TaskSummaryResponse]:
    return [TaskSummaryResponse.model_validate(item) for item in asset_service.list_tasks_for_asset(actor, asset_id)]


@router.get("/tickets/{ticket_id}/assets", response_model=list[AssetSummaryResponse])
def list_ticket_assets(
    ticket_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[AssetSummaryResponse]:
    return [AssetSummaryResponse.model_validate(item) for item in asset_service.list_assets_for_ticket(actor, ticket_id)]


@router.post("/tickets/{ticket_id}/assets", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def link_asset_to_ticket(
    ticket_id: str,
    payload: LinkAssetRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> Response:
    asset_service.link_asset_to_ticket(actor, ticket_id, payload.asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/tickets/{ticket_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def unlink_asset_from_ticket(
    ticket_id: str,
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> Response:
    asset_service.unlink_asset_from_ticket(actor, ticket_id, asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tasks/{task_id}/assets", response_model=list[AssetSummaryResponse])
def list_task_assets(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> list[AssetSummaryResponse]:
    return [AssetSummaryResponse.model_validate(item) for item in asset_service.list_assets_for_task(actor, task_id)]


@router.post("/tasks/{task_id}/assets", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def link_asset_to_task(
    task_id: str,
    payload: LinkAssetRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> Response:
    asset_service.link_asset_to_task(actor, task_id, payload.asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/tasks/{task_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def unlink_asset_from_task(
    task_id: str,
    asset_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    asset_service: AssetApplicationService = Depends(get_asset_application_service),
) -> Response:
    asset_service.unlink_asset_from_task(actor, task_id, asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
