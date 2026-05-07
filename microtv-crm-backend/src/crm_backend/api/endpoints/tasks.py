"""HTTP endpoints for the task module."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_task_application_service
from crm_backend.schemas import (
    ApproveTaskRequest,
    AssignSubtaskRequest,
    CreateTaskFromTemplateRequest,
    CreateTaskTemplateRequest,
    ErrorResponse,
    ExecuteSubtaskActionRequest,
    RejectTaskApprovalRequest,
    SetTaskTemplateActivationRequest,
    TaskAttachmentResponse,
    TaskDetailResponse,
    TaskSummaryResponse,
    TaskTemplateResponse,
    UpdateTaskTemplateRequest,
    UnassignedSubtaskQueueResponse,
    UpdateSubtaskProgressRequest,
)
from crm_backend.services import TaskApplicationService
from crm_backend.services.auth_service import ResolvedCrmSession


router = APIRouter(prefix="/tasks", tags=["tasks"])
_logger = logging.getLogger(__name__)


def _safe_task_summary_list(items: list[object]) -> list[TaskSummaryResponse]:
    response: list[TaskSummaryResponse] = []
    for index, item in enumerate(items):
        try:
            response.append(TaskSummaryResponse.model_validate(item))
        except Exception:
            _logger.exception("Failed to serialize task summary item at index %s", index)
    return response


def _safe_unassigned_subtask_list(items: list[object]) -> list[UnassignedSubtaskQueueResponse]:
    response: list[UnassignedSubtaskQueueResponse] = []
    for index, item in enumerate(items):
        try:
            response.append(_map_unassigned_subtask(item))
        except Exception:
            _logger.exception("Failed to serialize unassigned subtask item at index %s", index)
    return response


def _map_unassigned_subtask(subtask) -> UnassignedSubtaskQueueResponse:
    return UnassignedSubtaskQueueResponse(
        task_id=subtask.task.task_id,
        client_id=subtask.task.client_id,
        client_name=subtask.task.client_name,
        template_id=subtask.task.template_id,
        template_name=subtask.task.template_name,
        task_title=subtask.task.task_title,
        subtask_id=subtask.subtask_id,
        subtask_title=subtask.subtask_title,
        responsible_role_key=subtask.responsible_role_key,
        status=subtask.status,
        order_index=subtask.order_index,
    )


@router.post(
    "/templates",
    response_model=TaskTemplateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_template(
    payload: CreateTaskTemplateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskTemplateResponse:
    return TaskTemplateResponse.model_validate(task_service.create_template(actor, payload))


@router.get(
    "/templates",
    response_model=list[TaskTemplateResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_templates(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskTemplateResponse]:
    return [TaskTemplateResponse.model_validate(item) for item in task_service.list_templates(actor)]


@router.get(
    "/templates/{template_id}",
    response_model=TaskTemplateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_template_detail(
    template_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskTemplateResponse:
    return TaskTemplateResponse.model_validate(task_service.get_template_detail(actor, template_id))


@router.put(
    "/templates/{template_id}",
    response_model=TaskTemplateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_template(
    template_id: str,
    payload: UpdateTaskTemplateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskTemplateResponse:
    return TaskTemplateResponse.model_validate(task_service.update_template(actor, template_id, payload))


@router.patch(
    "/templates/{template_id}/activation",
    response_model=TaskTemplateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def set_template_activation(
    template_id: str,
    payload: SetTaskTemplateActivationRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskTemplateResponse:
    return TaskTemplateResponse.model_validate(task_service.set_template_active(actor, template_id, payload))


@router.post(
    "/{task_id}/attachments",
    response_model=list[TaskAttachmentResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def upload_task_attachments(
    task_id: str,
    files: Annotated[list[UploadFile], File(...)],
    subtask_id: Annotated[str | None, Form()] = None,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskAttachmentResponse]:
    return [
        TaskAttachmentResponse.model_validate(item)
        for item in await task_service.upload_task_attachments(actor, task_id, subtask_id, files)
    ]


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def delete_task_attachment(
    attachment_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> Response:
    task_service.delete_task_attachment(actor, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_task_from_template(
    payload: CreateTaskFromTemplateRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.create_task_from_template(actor, payload))


@router.get(
    "/assigned/me",
    response_model=list[TaskSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_my_assigned_tasks(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskSummaryResponse]:
    return _safe_task_summary_list(task_service.list_tasks_assigned_to_actor(actor))


@router.get(
    "/tracking/me",
    response_model=list[TaskSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_tracking_tasks_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskSummaryResponse]:
    return _safe_task_summary_list(task_service.list_tracking_tasks_for_actor(actor))


@router.get(
    "/history/me",
    response_model=list[TaskSummaryResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_task_history_for_me(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskSummaryResponse]:
    return _safe_task_summary_list(task_service.list_task_history_for_actor(actor))


@router.get(
    "/unassigned/me",
    response_model=list[UnassignedSubtaskQueueResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_unassigned_subtasks_for_my_roles(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[UnassignedSubtaskQueueResponse]:
    return _safe_unassigned_subtask_list(task_service.list_unassigned_subtasks_for_actor(actor))


@router.post(
    "/subtasks/{subtask_id}/claim",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def claim_subtask(
    subtask_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.claim_unassigned_subtask(actor, subtask_id))


@router.patch(
    "/subtasks/{subtask_id}/assignment",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def assign_subtask(
    subtask_id: str,
    payload: AssignSubtaskRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(
        task_service.assign_subtask(actor, subtask_id, payload.assigned_crm_user_id, payload.notes)
    )


@router.patch(
    "/{task_id}/approve",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def approve_task(
    task_id: str,
    payload: ApproveTaskRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.approve_task(actor, task_id, payload))


@router.patch(
    "/{task_id}/reject",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def reject_task_approval(
    task_id: str,
    payload: RejectTaskApprovalRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.reject_task_approval(actor, task_id, payload))


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_task_detail(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.get_task_detail(actor, task_id))


@router.put(
    "/subtasks/{subtask_id}/items",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def update_subtask_progress(
    subtask_id: str,
    payload: UpdateSubtaskProgressRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.update_subtask_progress(actor, subtask_id, payload))


@router.post(
    "/subtasks/{subtask_id}/actions",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def execute_subtask_action(
    subtask_id: str,
    payload: ExecuteSubtaskActionRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(task_service.execute_subtask_action(actor, subtask_id, payload))