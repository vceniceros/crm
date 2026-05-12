"""Repositorio para suscripciones push."""

from __future__ import annotations

from sqlalchemy.orm import Session

from crm_backend.models.push_subscription import PushSubscription


class PushSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, crm_user_id: str, endpoint: str, p256dh: str, auth: str, user_agent: str | None = None) -> PushSubscription:
        existing = self._session.query(PushSubscription).filter_by(endpoint=endpoint).first()
        if existing:
            existing.crm_user_id = crm_user_id
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_agent = user_agent
            self._session.flush()
            return existing

        subscription = PushSubscription(
            crm_user_id=crm_user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
        )
        self._session.add(subscription)
        self._session.flush()
        return subscription

    def delete_by_endpoint(self, endpoint: str) -> None:
        self._session.query(PushSubscription).filter_by(endpoint=endpoint).delete()
        self._session.flush()

    def list_for_user(self, crm_user_id: str) -> list[PushSubscription]:
        return self._session.query(PushSubscription).filter_by(crm_user_id=crm_user_id).all()
