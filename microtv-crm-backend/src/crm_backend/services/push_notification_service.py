"""Servicio de envio de push notifications via VAPID/Web Push."""

from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush

from crm_backend.core.config import Settings
from crm_backend.repositories.push_subscription_repository import PushSubscriptionRepository

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(
        self,
        push_subscription_repository: PushSubscriptionRepository,
        settings: Settings,
    ) -> None:
        self._repo = push_subscription_repository
        self._settings = settings

    def send_to_user(self, crm_user_id: str, title: str, body: str, url: str | None = None) -> None:
        """Envia una push notification a todos los dispositivos del usuario.

        Los errores de envio se loguean y no se propagan para no romper el
        flujo de negocio que dispara la notificacion in-app.
        """

        if not self._settings.vapid_private_key:
            return

        try:
            subscriptions = self._repo.list_for_user(crm_user_id)
        except Exception as exc:
            logger.warning(
                "Push dispatch skipped for user %s: failed to load subscriptions: %s",
                crm_user_id,
                exc,
            )
            return

        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "url": url or "/",
                "notification": {
                    "title": title,
                    "body": body,
                    "data": {"url": url or "/"},
                },
            }
        )

        stale_endpoints: list[str] = []

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=self._settings.vapid_private_key,
                    vapid_claims={"sub": self._settings.vapid_claims_sub},
                )
            except WebPushException as exc:
                response = getattr(exc, "response", None)
                status_code = response.status_code if response is not None else None
                if status_code == 410:
                    stale_endpoints.append(sub.endpoint)
                else:
                    logger.warning("Push send failed for user %s endpoint %s: %s", crm_user_id, sub.endpoint, exc)
            except Exception as exc:
                logger.warning("Push send unexpected error for user %s: %s", crm_user_id, exc)

        for endpoint in stale_endpoints:
            try:
                self._repo.delete_by_endpoint(endpoint)
            except Exception as exc:
                logger.warning("Failed to remove stale push subscription: %s", exc)
