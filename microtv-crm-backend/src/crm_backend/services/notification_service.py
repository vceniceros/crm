"""Application service for creating and querying in-app notifications."""

from __future__ import annotations

import logging

from crm_backend.models.notification import Notification, NotificationEntityType, NotificationType
from crm_backend.repositories.crm_user_repository import CrmUserRepository
from crm_backend.repositories.notification_repository import NotificationRepository
from crm_backend.core.exceptions import NotificationNotFoundError, NotificationAccessDeniedError
from crm_backend.services.push_notification_service import PushNotificationService


logger = logging.getLogger(__name__)


class NotificationService:
    """Create, list, and mark notifications for CRM users."""

    def __init__(
        self,
        notification_repository: NotificationRepository,
        user_repository: CrmUserRepository,
        push_notification_service: PushNotificationService | None = None,
    ) -> None:
        self._notification_repository = notification_repository
        self._user_repository = user_repository
        self._push_notification_service = push_notification_service

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_for_user(self, crm_user_id: str, limit: int = 20) -> list[Notification]:
        return self._notification_repository.list_for_user(crm_user_id, limit=limit)

    def count_unread(self, crm_user_id: str) -> int:
        return self._notification_repository.count_unread_for_user(crm_user_id)

    # ------------------------------------------------------------------
    # Mark read
    # ------------------------------------------------------------------

    def mark_read(self, crm_user_id: str, notification_id: str) -> Notification:
        notification = self._notification_repository.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError()
        if notification.recipient_crm_user_id != crm_user_id:
            raise NotificationAccessDeniedError()
        if notification.is_read:
            return notification
        return self._notification_repository.mark_read(notification)

    def mark_all_read(self, crm_user_id: str) -> int:
        return self._notification_repository.mark_all_read_for_user(crm_user_id)

    # ------------------------------------------------------------------
    # Creation helpers — called from business service events
    # ------------------------------------------------------------------

    def notify(
        self,
        *,
        recipient_crm_user_id: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        entity_type: NotificationEntityType | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
    ) -> Notification:
        notification = Notification(
            recipient_crm_user_id=recipient_crm_user_id,
            notification_type=notification_type.value,
            title=title,
            body=body,
            entity_type=entity_type.value if entity_type is not None else None,
            entity_id=entity_id,
            metadata_json=metadata,
        )
        saved = self._notification_repository.save(notification)

        if self._push_notification_service is not None:
            try:
                self._push_notification_service.send_to_user(
                    crm_user_id=recipient_crm_user_id,
                    title=title,
                    body=body,
                )
            except Exception as exc:
                logger.warning("Push dispatch failed for notification %s: %s", saved.notification_id, exc)

        return saved

    def notify_bulk(
        self,
        *,
        recipient_crm_user_ids: list[str],
        notification_type: NotificationType,
        title: str,
        body: str,
        entity_type: NotificationEntityType | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        if not recipient_crm_user_ids:
            return
        notifications = [
            Notification(
                recipient_crm_user_id=user_id,
                notification_type=notification_type.value,
                title=title,
                body=body,
                entity_type=entity_type.value if entity_type is not None else None,
                entity_id=entity_id,
                metadata_json=metadata,
            )
            for user_id in recipient_crm_user_ids
        ]
        self._notification_repository.save_bulk(notifications)

        if self._push_notification_service is not None:
            for user_id in recipient_crm_user_ids:
                try:
                    self._push_notification_service.send_to_user(
                        crm_user_id=user_id,
                        title=title,
                        body=body,
                    )
                except Exception as exc:
                    logger.warning("Push bulk dispatch failed for user %s: %s", user_id, exc)

    # ------------------------------------------------------------------
    # Role-based recipient resolution helpers
    # ------------------------------------------------------------------

    def resolve_users_with_role_key(self, role_key: str) -> list[str]:
        """Return crm_user_ids for all active users that hold the given role key."""
        users = self._user_repository.list_active_by_role_key(role_key)
        return [u.crm_user_id for u in users]
