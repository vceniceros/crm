"""Endpoints REST para gestion de suscripciones push."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from crm_backend.api.dependencies import (
    get_authenticated_crm_session,
    get_push_subscription_repository,
)
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository
from crm_backend.schemas.common import ErrorResponse
from crm_backend.services.auth_service import ResolvedCrmSession

router = APIRouter(prefix="/notifications/push-subscription", tags=["push-notifications"])


class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str | None = None


class DeletePushSubscriptionBody(BaseModel):
    endpoint: str


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
def upsert_push_subscription(
    body: PushSubscriptionBody,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
) -> None:
    repo.upsert(
        crm_user_id=actor.crm_user.crm_user_id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
        user_agent=body.user_agent,
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
def delete_push_subscription(
    body: DeletePushSubscriptionBody,
    actor: ResolvedCrmSession = Depends(get_authenticated_crm_session),
    repo: PushSubscriptionRepository = Depends(get_push_subscription_repository),
) -> None:
    user_endpoints = {subscription.endpoint for subscription in repo.list_for_user(actor.crm_user.crm_user_id)}
    if body.endpoint not in user_endpoints:
        return

    repo.delete_by_endpoint(body.endpoint)
