"""HTTP endpoints for the task module."""

from datetime import UTC, datetime
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from crm_backend.api.dependencies import (
    get_authenticated_crm_session,
    get_task_application_service,
    get_task_export_service,
    get_task_pre_form_service,
    get_task_satisfaction_form_service,
)
from crm_backend.core.exceptions import SatisfactionFormNotFoundError, TaskPreFormNotFoundError
from crm_backend.schemas import (
    ApproveTaskRequest,
    AssignSubtaskRequest,
    CreateTaskCommentRequest,
    CreateTaskFromTemplateRequest,
    CreateTaskTemplateRequest,
    ErrorResponse,
    ExecuteSubtaskActionRequest,
    GenerateTaskSatisfactionFormResponse,
    PublicTaskPreFormInfoResponse,
    PublicTaskSatisfactionFormInfoResponse,
    RejectTaskApprovalRequest,
    SetTaskTemplateActivationRequest,
    SubmitTaskPreFormRequest,
    SubmitTaskSatisfactionFormRequest,
    TaskAttachmentResponse,
    TaskDetailResponse,
    TaskPreFormStatusResponse,
    TaskSatisfactionFormStatusResponse,
    TaskSatisfactionResponseDetailResponse,
    TaskSummaryResponse,
    TaskTemplateResponse,
    UpdateTaskTemplateRequest,
    UnassignedSubtaskQueueResponse,
    UpdateSubtaskProgressRequest,
)
from crm_backend.services import TaskApplicationService, TaskExportService, TaskPreFormService, TaskSatisfactionFormService
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


def _build_export_response(task, zip_bytes: bytes) -> StreamingResponse:
    task_number = task.task_id
    date_label = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"pedido_{task_number}_{date_label}.zip"
    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _map_task_satisfaction_response(response) -> TaskSatisfactionResponseDetailResponse:
    return TaskSatisfactionResponseDetailResponse(
        response_id=response.response_id,
        task_id=response.task_id,
        customer_name=response.customer_name,
        customer_company=response.customer_company,
        rating=response.rating,
        comment=response.comment,
        submitted_at=response.submitted_at,
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
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(...)],
    subtask_id: Annotated[str | None, Form()] = None,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> list[TaskAttachmentResponse]:
    return [
        TaskAttachmentResponse.model_validate(item)
        for item in await task_service.upload_task_attachments(actor, task_id, subtask_id, files, background_tasks)
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
    "/{task_id}/comments",
    response_model=TaskDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def add_task_comment(
    task_id: str,
    payload: CreateTaskCommentRequest,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
) -> TaskDetailResponse:
    return TaskDetailResponse.model_validate(
        task_service.add_task_comment(
            actor,
            task_id,
            body=payload.body,
            location_id=payload.location_id,
            attachment_ids=payload.attachment_ids,
            mentioned_user_ids=payload.mentioned_user_ids,
        )
    )


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


@router.get(
    "/{task_id}/export",
    responses={
        200: {"content": {"application/zip": {}}, "description": "ZIP archive with PDF + multimedia"},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def export_task_history(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    export_service: TaskExportService = Depends(get_task_export_service),
) -> StreamingResponse:
    task = task_service.get_task_detail(actor, task_id)
    zip_bytes = export_service.export_development_zip(actor, task)
    return _build_export_response(task, zip_bytes)


@router.post(
    "/{task_id}/satisfaction-form",
    response_model=GenerateTaskSatisfactionFormResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def generate_task_satisfaction_form(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    sat_service: TaskSatisfactionFormService = Depends(get_task_satisfaction_form_service),
) -> GenerateTaskSatisfactionFormResponse:
    task = task_service.get_task_detail(actor, task_id)
    form, raw_token = sat_service.generate_form(actor, task)
    return GenerateTaskSatisfactionFormResponse(
        form_id=form.form_id,
        task_id=form.task_id,
        public_link_token=raw_token,
        survey_path=f"/satisfaction/{raw_token}?mode=task",
        expires_at=form.expires_at,
        status_label=form.status_label,
    )


@router.get(
    "/{task_id}/satisfaction-form/status",
    response_model=TaskSatisfactionFormStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_task_satisfaction_form_status(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    sat_service: TaskSatisfactionFormService = Depends(get_task_satisfaction_form_service),
) -> TaskSatisfactionFormStatusResponse:
    task = task_service.get_task_detail(actor, task_id)
    form = sat_service.get_form_status(actor, task)
    if form is None:
        raise SatisfactionFormNotFoundError()
    return TaskSatisfactionFormStatusResponse.from_orm_form(form)


@router.get(
    "/{task_id}/satisfaction-response",
    response_model=TaskSatisfactionResponseDetailResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_task_satisfaction_response(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    sat_service: TaskSatisfactionFormService = Depends(get_task_satisfaction_form_service),
) -> TaskSatisfactionResponseDetailResponse:
    task = task_service.get_task_detail(actor, task_id)
    response = sat_service.get_response_for_task(actor, task)
    if response is None:
        raise SatisfactionFormNotFoundError()
    return _map_task_satisfaction_response(response)


@router.post(
    "/{task_id}/pre-form/generate",
    response_model=TaskPreFormStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def generate_task_pre_form_link(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    pre_form_service: TaskPreFormService = Depends(get_task_pre_form_service),
) -> TaskPreFormStatusResponse:
    task = task_service.get_task_detail(actor, task_id)
    instance, raw_token = pre_form_service.generate_or_regenerate_link(actor, task)
    return TaskPreFormStatusResponse(
        instance_id=instance.instance_id,
        task_id=instance.task_id,
        status_label=("respondido" if instance.submitted_at else "pendiente"),
        expires_at=instance.expires_at,
        submitted_at=instance.submitted_at,
        revoked_at=instance.revoked_at,
        form_link_path=f"/pre-form/{raw_token}",
        response_values=[],
        attachments=[],
    )


@router.get(
    "/{task_id}/pre-form/status",
    response_model=TaskPreFormStatusResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_task_pre_form_status(
    task_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    task_service: TaskApplicationService = Depends(get_task_application_service),
    pre_form_service: TaskPreFormService = Depends(get_task_pre_form_service),
) -> TaskPreFormStatusResponse:
    task = task_service.get_task_detail(actor, task_id)
    instance = pre_form_service.get_status(actor, task)
    if instance is None:
        raise TaskPreFormNotFoundError()

    response_values = []
    if instance.response is not None and instance.template_pre_form is not None:
        field_lookup = {field.field_id: field for field in instance.template_pre_form.fields}
        for field_value in instance.response.field_values:
            field = field_lookup.get(field_value.field_id)
            if field is None:
                continue
            response_values.append(
                {
                    "field_id": field.field_id,
                    "label": field.label,
                    "field_type": field.field_type,
                    "text_value": field_value.text_value,
                    "file_attachment_id": field_value.file_attachment_id,
                    "file_url": field_value.attachment.file_url if field_value.attachment is not None else None,
                }
            )

    attachments = [
        {
            "attachment_id": attachment.attachment_id,
            "file_url": attachment.file_url,
            "mime_type": attachment.mime_type,
            "uploaded_at": attachment.uploaded_at,
        }
        for attachment in instance.attachments
    ]

    return TaskPreFormStatusResponse(
        instance_id=instance.instance_id,
        task_id=instance.task_id,
        status_label=("respondido" if instance.submitted_at else "pendiente"),
        expires_at=instance.expires_at,
        submitted_at=instance.submitted_at,
        revoked_at=instance.revoked_at,
        form_link_path=None,
        response_values=response_values,
        attachments=attachments,
    )
