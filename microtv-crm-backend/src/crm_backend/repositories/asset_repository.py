"""Repository for asset aggregates."""

from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import Asset, AssetCategory, AssetFieldValue, Task, TaskAsset, Ticket, TicketAsset


class AssetRepository:
    """Persist and query asset categories, assets, and links."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def save_category(self, category: AssetCategory) -> AssetCategory:
        self._session.add(category)
        self._session.commit()
        self._session.refresh(category)
        return self.get_category(category.asset_category_id) or category

    def get_category(self, category_id: str) -> AssetCategory | None:
        statement = select(AssetCategory).options(selectinload(AssetCategory.fields)).where(AssetCategory.asset_category_id == category_id)
        return self._session.scalar(statement)

    def list_categories(self, is_active: bool | None = True) -> list[AssetCategory]:
        statement = select(AssetCategory).options(selectinload(AssetCategory.fields))
        if is_active is not None:
            statement = statement.where(AssetCategory.is_active.is_(is_active))
        return list(self._session.scalars(statement.order_by(AssetCategory.category_name.asc())).all())

    def save_asset(self, asset: Asset) -> Asset:
        self._session.add(asset)
        self._session.commit()
        self._session.refresh(asset)
        return self.get_asset(asset.asset_id) or asset

    def get_asset(self, asset_id: str) -> Asset | None:
        statement = (
            select(Asset)
            .options(selectinload(Asset.field_values).selectinload(AssetFieldValue.field))
            .where(Asset.asset_id == asset_id, Asset.deleted_at.is_(None))
        )
        return self._session.scalar(statement)

    def list_assets(self, client_id: str | None = None, category_id: str | None = None, search: str | None = None) -> list[Asset]:
        statement = select(Asset).options(selectinload(Asset.field_values).selectinload(AssetFieldValue.field)).where(Asset.deleted_at.is_(None))
        if client_id:
            statement = statement.where(Asset.client_id == client_id)
        if category_id:
            statement = statement.where(Asset.category_id == category_id)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(or_(Asset.asset_name.ilike(pattern), Asset.notes.ilike(pattern)))
        return list(self._session.scalars(statement.order_by(Asset.updated_at.desc(), Asset.asset_name.asc())).unique().all())

    def get_asset_with_links(self, asset_id: str) -> Asset | None:
        return self.get_asset(asset_id)

    def link_to_ticket(self, ticket_id: str, asset_id: str, actor_user_id: str) -> None:
        exists = self._session.scalar(select(TicketAsset).where(TicketAsset.ticket_id == ticket_id, TicketAsset.asset_id == asset_id))
        if exists is None:
            self._session.add(TicketAsset(ticket_id=ticket_id, asset_id=asset_id, linked_by_crm_user_id=actor_user_id))
            self._session.commit()

    def unlink_from_ticket(self, ticket_id: str, asset_id: str) -> None:
        self._session.execute(delete(TicketAsset).where(TicketAsset.ticket_id == ticket_id, TicketAsset.asset_id == asset_id))
        self._session.commit()

    def link_to_task(self, task_id: str, asset_id: str, actor_user_id: str) -> None:
        exists = self._session.scalar(select(TaskAsset).where(TaskAsset.task_id == task_id, TaskAsset.asset_id == asset_id))
        if exists is None:
            self._session.add(TaskAsset(task_id=task_id, asset_id=asset_id, linked_by_crm_user_id=actor_user_id))
            self._session.commit()

    def unlink_from_task(self, task_id: str, asset_id: str) -> None:
        self._session.execute(delete(TaskAsset).where(TaskAsset.task_id == task_id, TaskAsset.asset_id == asset_id))
        self._session.commit()

    def unlink_asset_everywhere(self, asset_id: str) -> None:
        self._session.execute(delete(TicketAsset).where(TicketAsset.asset_id == asset_id))
        self._session.execute(delete(TaskAsset).where(TaskAsset.asset_id == asset_id))

    def list_assets_for_ticket(self, ticket_id: str) -> list[Asset]:
        statement = (
            select(Asset)
            .join(TicketAsset, TicketAsset.asset_id == Asset.asset_id)
            .options(selectinload(Asset.field_values).selectinload(AssetFieldValue.field))
            .where(TicketAsset.ticket_id == ticket_id, Asset.deleted_at.is_(None))
            .order_by(Asset.asset_name.asc())
        )
        return list(self._session.scalars(statement).unique().all())

    def list_assets_for_task(self, task_id: str) -> list[Asset]:
        statement = (
            select(Asset)
            .join(TaskAsset, TaskAsset.asset_id == Asset.asset_id)
            .options(selectinload(Asset.field_values).selectinload(AssetFieldValue.field))
            .where(TaskAsset.task_id == task_id, Asset.deleted_at.is_(None))
            .order_by(Asset.asset_name.asc())
        )
        return list(self._session.scalars(statement).unique().all())

    def list_tickets_for_asset(self, asset_id: str) -> list[Ticket]:
        statement = select(Ticket).join(TicketAsset, TicketAsset.ticket_id == Ticket.ticket_id).where(TicketAsset.asset_id == asset_id)
        return list(self._session.scalars(statement.order_by(Ticket.updated_at.desc())).unique().all())

    def list_tasks_for_asset(self, asset_id: str) -> list[Task]:
        statement = select(Task).join(TaskAsset, TaskAsset.task_id == Task.task_id).where(TaskAsset.asset_id == asset_id)
        return list(self._session.scalars(statement.order_by(Task.updated_at.desc())).unique().all())
