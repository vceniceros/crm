"""Public (unauthenticated) task endpoints for satisfaction and pre-forms."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from crm_backend.api.dependencies import get_task_pre_form_service, get_task_satisfaction_form_service
from crm_backend.schemas.tasks import (
    PublicTaskPreFormInfoResponse,
    PublicTaskSatisfactionFormInfoResponse,
    SubmitTaskPreFormRequest,
    SubmitTaskSatisfactionFormRequest,
    TaskSatisfactionResponseDetailResponse,
)
from crm_backend.services.task_pre_form_service import TaskPreFormService
from crm_backend.services.task_satisfaction_form_service import TaskSatisfactionFormService

router = APIRouter(tags=["public-tasks"])


def _get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/public/tasks/satisfaction/{token}",
    response_model=PublicTaskSatisfactionFormInfoResponse,
    responses={404: {"description": "Form not found, expired or already used"}},
)
def get_public_task_satisfaction_form(
    token: str,
    sat_service: TaskSatisfactionFormService = Depends(get_task_satisfaction_form_service),
) -> PublicTaskSatisfactionFormInfoResponse:
    form = sat_service.get_public_form_info(token)
    task = form.task

    client_name: str | None = None
    location_name: str | None = None
    if task.client is not None:
        client_name = getattr(task.client, "business_name", None)
    if task.location is not None:
        location_name = getattr(task.location, "formatted_address", None) or getattr(task.location, "address_label", None)

    return PublicTaskSatisfactionFormInfoResponse(
        task_title=task.task_title,
        client_name=client_name,
        location_name=location_name,
        status_label=form.status_label,
    )


@router.post(
    "/public/tasks/satisfaction/{token}",
    response_model=TaskSatisfactionResponseDetailResponse,
    responses={404: {"description": "Form not found, expired or already used"}, 409: {"description": "Already responded"}, 422: {"description": "Validation error"}},
)
def submit_public_task_satisfaction_form(
    token: str,
    payload: SubmitTaskSatisfactionFormRequest,
    request: Request,
    sat_service: TaskSatisfactionFormService = Depends(get_task_satisfaction_form_service),
) -> TaskSatisfactionResponseDetailResponse:
    response = sat_service.submit_response(
        raw_token=token,
        rating=payload.rating,
        customer_name=payload.customer_name,
        customer_company=payload.customer_company,
        comment=payload.comment,
        submitter_ip=_get_client_ip(request),
        submitter_user_agent=request.headers.get("User-Agent"),
    )
    return TaskSatisfactionResponseDetailResponse(
        response_id=response.response_id,
        task_id=response.task_id,
        customer_name=response.customer_name,
        customer_company=response.customer_company,
        rating=response.rating,
        comment=response.comment,
        submitted_at=response.submitted_at,
    )


@router.get(
    "/pre-form/{token}",
    response_model=PublicTaskPreFormInfoResponse,
    responses={404: {"description": "Form not found, expired or already used"}},
)
def get_public_task_pre_form(
    token: str,
    pre_form_service: TaskPreFormService = Depends(get_task_pre_form_service),
) -> PublicTaskPreFormInfoResponse:
    instance = pre_form_service.get_public_form_info(token)
    task = instance.task
    template_form = instance.template_pre_form

    client_name: str | None = None
    location_name: str | None = None
    if task.client is not None:
        client_name = getattr(task.client, "business_name", None)
    if task.location is not None:
        location_name = getattr(task.location, "formatted_address", None) or getattr(task.location, "address_label", None)

    return PublicTaskPreFormInfoResponse(
        task_title=task.task_title,
        client_name=client_name,
        location_name=location_name,
        title=(template_form.title if template_form is not None else None),
        instructions=(template_form.instructions if template_form is not None else None),
        fields=list(template_form.fields if template_form is not None else []),
    )


@router.post(
    "/pre-form/{token}",
    response_model=dict,
    responses={404: {"description": "Form not found, expired or already used"}, 409: {"description": "Already responded"}, 422: {"description": "Validation error"}},
)
def submit_public_task_pre_form(
    token: str,
    payload: SubmitTaskPreFormRequest,
    request: Request,
    pre_form_service: TaskPreFormService = Depends(get_task_pre_form_service),
) -> dict:
    response = pre_form_service.submit_response(
        raw_token=token,
        values=[value.model_dump() for value in payload.values],
        submitter_ip=_get_client_ip(request),
    )
    return {
        "response_id": response.response_id,
        "task_id": response.task_id,
        "submitted_at": response.submitted_at,
        "status": "ok",
    }
