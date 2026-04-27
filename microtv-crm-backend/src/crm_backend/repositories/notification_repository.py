"""Repository for notification persistence and querying."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crm_backend.models.notification import Notification


class NotificationRepository:
    """Persist and query per-user notifications."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, notification: Notification) -> Notification:
        self._session.add(notification)
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def save_bulk(self, notifications: list[Notification]) -> None:
        for notification in notifications:
            self._session.add(notification)
        self._session.commit()

    def list_for_user(self, recipient_crm_user_id: str, limit: int = 20) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.recipient_crm_user_id == recipient_crm_user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def count_unread_for_user(self, recipient_crm_user_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_crm_user_id == recipient_crm_user_id,
                Notification.is_read.is_(False),
            )
        )
        return self._session.scalar(stmt) or 0

    def get_by_id(self, notification_id: str) -> Notification | None:
        return self._session.scalar(
            select(Notification).where(Notification.notification_id == notification_id)
        )

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        self._session.add(notification)
        self._session.commit()
        self._session.refresh(notification)
        return notification

    def mark_all_read_for_user(self, recipient_crm_user_id: str) -> int:
        now = datetime.now(UTC)
        stmt = (
            select(Notification)
            .where(
                Notification.recipient_crm_user_id == recipient_crm_user_id,
                Notification.is_read.is_(False),
            )
        )
        notifications = list(self._session.scalars(stmt))
        for n in notifications:
            n.is_read = True
            n.read_at = now
        self._session.commit()
        return len(notifications)
