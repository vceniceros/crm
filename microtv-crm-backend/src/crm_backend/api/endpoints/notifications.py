"""HTTP endpoints for the in-app notification module."""

from fastapi import APIRouter, Depends, status

from crm_backend.api.dependencies import get_authenticated_crm_session, get_notification_service
from crm_backend.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from crm_backend.schemas.common import ErrorResponse
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def list_notifications(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    notifications = notification_service.list_for_user(actor.crm_user.crm_user_id)
    unread_count = notification_service.count_unread(actor.crm_user.crm_user_id)
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def get_unread_count(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    notification_service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    count = notification_service.count_unread(actor.crm_user.crm_user_id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def mark_notification_read(
    notification_id: str,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    notification = notification_service.mark_read(actor.crm_user.crm_user_id, notification_id)
    return NotificationResponse.model_validate(notification)


@router.post(
    "/mark-all-read",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def mark_all_notifications_read(
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    notification_service: NotificationService = Depends(get_notification_service),
) -> None:
    notification_service.mark_all_read(actor.crm_user.crm_user_id)
