"""HTTP endpoints for material requirements, requests, and dispatches."""

from fastapi import APIRouter, Depends

from crm_backend.api.dependencies import (
    get_authenticated_crm_session,
    get_inventory_request_facade,
    get_task_material_flow_facade,
)
from crm_backend.schemas import (
    ConfirmDispatchItemRequest,
    CreateInventoryRequestRequest,
    CreateTaskDispatchRequest,
    ErrorResponse,
    InventoryDispatchResponse,
    InventoryRequestResponse,
    InventorySourceFlowResponse,
    ReviewInventoryRequestRequest,
    TaskDetailResponse,
)
from crm_backend.services import InventoryRequestFacade, TaskMaterialFlowFacade
from crm_backend.services.auth_service import ResolvedCrmSession


router = APIRouter(prefix="/inventory-flow", tags=["inventory-flow"])


@router.post(
    "/requests",
    response_model=InventoryRequestResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_inventory_request(
    payload: CreateInventoryRequestRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    inventory_request_facade: InventoryRequestFacade = Depends(get_inventory_request_facade),
) -> InventoryRequestResponse:
    return InventoryRequestResponse.model_validate(inventory_request_facade.create_request(actor, payload))


@router.post(
    "/requests/{request_id}/review",
    response_model=InventoryRequestResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def review_inventory_request(
    request_id: str,
    payload: ReviewInventoryRequestRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    inventory_request_facade: InventoryRequestFacade = Depends(get_inventory_request_facade),
) -> InventoryRequestResponse:
    return InventoryRequestResponse.model_validate(inventory_request_facade.review_request(actor, request_id, payload))


@router.post(
    "/requests/{request_id}/dispatches",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def dispatch_inventory_request(
    request_id: str,
    payload: CreateTaskDispatchRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    inventory_request_facade: InventoryRequestFacade = Depends(get_inventory_request_facade),
) -> InventoryDispatchResponse | TaskDetailResponse:
    result = inventory_request_facade.dispatch_request(actor, request_id, payload)
    if hasattr(result, "subtasks"):
        return TaskDetailResponse.model_validate(result)
    return InventoryDispatchResponse.model_validate(result)


@router.get(
    "/requests/open",
    response_model=list[InventoryRequestResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_open_inventory_requests(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    inventory_request_facade: InventoryRequestFacade = Depends(get_inventory_request_facade),
) -> list[InventoryRequestResponse]:
    return [InventoryRequestResponse.model_validate(item) for item in inventory_request_facade.list_open_requests(actor)]


@router.get(
    "/sources/{source_type}/{source_reference_id}",
    response_model=InventorySourceFlowResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_inventory_source_flow(
    source_type: str,
    source_reference_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    inventory_request_facade: InventoryRequestFacade = Depends(get_inventory_request_facade),
) -> InventorySourceFlowResponse:
    normalized_source_type = source_type.upper()
    requests, dispatches = inventory_request_facade.list_source_flow(
        actor,
        source_type=normalized_source_type,
        source_reference_id=source_reference_id,
    )
    return InventorySourceFlowResponse(
        source_type=normalized_source_type,
        source_reference_id=source_reference_id,
        requests=[InventoryRequestResponse.model_validate(item) for item in requests],
        dispatches=[InventoryDispatchResponse.model_validate(item) for item in dispatches],
    )


@router.post(
    "/tasks/{task_id}/dispatches",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_task_dispatch(
    task_id: str,
    payload: CreateTaskDispatchRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_material_flow: TaskMaterialFlowFacade = Depends(get_task_material_flow_facade),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_material_flow.create_task_dispatch(actor, task_id, payload))


@router.post(
    "/dispatch-items/{dispatch_item_id}/confirmations",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def confirm_dispatch_item(
    dispatch_item_id: str,
    payload: ConfirmDispatchItemRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_material_flow: TaskMaterialFlowFacade = Depends(get_task_material_flow_facade),
) -> InventoryDispatchResponse | TaskDetailResponse:
    result = task_material_flow.confirm_dispatch_item(actor, dispatch_item_id, payload)
    if hasattr(result, "subtasks"):
        return TaskDetailResponse.model_validate(result)
    return InventoryDispatchResponse.model_validate(result)