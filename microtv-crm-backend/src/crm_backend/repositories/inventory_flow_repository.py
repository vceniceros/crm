"""Repository for generic inventory request and dispatch flows."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import InventoryDispatch, InventoryDispatchItem, InventoryRequest, InventoryRequestItem


class InventoryFlowRepository:
    """Persist and query generic inventory requests and dispatches."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def save_request(self, request: InventoryRequest) -> InventoryRequest:
        self._session.add(request)
        self._session.commit()
        self._session.refresh(request)
        return self.get_request_by_id(request.request_id) or request

    def save_dispatch(self, dispatch: InventoryDispatch) -> InventoryDispatch:
        self._session.add(dispatch)
        self._session.commit()
        self._session.refresh(dispatch)
        return self.get_dispatch_by_id(dispatch.dispatch_id) or dispatch

    def get_request_by_id(self, request_id: str) -> InventoryRequest | None:
        statement = (
            select(InventoryRequest)
            .options(
                selectinload(InventoryRequest.items).selectinload(InventoryRequestItem.product),
                selectinload(InventoryRequest.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
            )
            .where(InventoryRequest.request_id == request_id)
        )
        return self._session.scalar(statement)

    def get_dispatch_by_id(self, dispatch_id: str) -> InventoryDispatch | None:
        statement = (
            select(InventoryDispatch)
            .options(selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product))
            .where(InventoryDispatch.dispatch_id == dispatch_id)
        )
        return self._session.scalar(statement)

    def get_dispatch_item_by_id(self, dispatch_item_id: str) -> InventoryDispatchItem | None:
        statement = (
            select(InventoryDispatchItem)
            .options(selectinload(InventoryDispatchItem.dispatch), selectinload(InventoryDispatchItem.product))
            .where(InventoryDispatchItem.dispatch_item_id == dispatch_item_id)
        )
        return self._session.scalar(statement)

    def list_requests_for_source(self, *, source_type: str, source_reference_id: str) -> list[InventoryRequest]:
        statement = (
            select(InventoryRequest)
            .options(
                selectinload(InventoryRequest.items).selectinload(InventoryRequestItem.product),
                selectinload(InventoryRequest.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
            )
            .where(InventoryRequest.source_type == source_type)
            .order_by(InventoryRequest.requested_at.desc())
        )
        if source_type == "TASK":
            statement = statement.where(InventoryRequest.task_id == source_reference_id)
        else:
            statement = statement.where(InventoryRequest.external_ticket_id == source_reference_id)
        return list(self._session.scalars(statement).all())

    def list_dispatches_for_source(self, *, source_type: str, source_reference_id: str) -> list[InventoryDispatch]:
        statement = (
            select(InventoryDispatch)
            .options(selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product))
            .where(InventoryDispatch.source_type == source_type)
            .order_by(InventoryDispatch.created_at.desc())
        )
        if source_type == "TASK":
            statement = statement.where(InventoryDispatch.task_id == source_reference_id)
        else:
            statement = statement.where(InventoryDispatch.external_ticket_id == source_reference_id)
        return list(self._session.scalars(statement).all())

    def list_open_requests(self) -> list[InventoryRequest]:
        statement = (
            select(InventoryRequest)
            .options(
                selectinload(InventoryRequest.items).selectinload(InventoryRequestItem.product),
                selectinload(InventoryRequest.dispatches).selectinload(InventoryDispatch.items).selectinload(InventoryDispatchItem.product),
            )
            .order_by(InventoryRequest.requested_at.desc())
        )
        return list(self._session.scalars(statement).all())
