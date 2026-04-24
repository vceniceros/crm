"""Repository for ticket aggregates."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from crm_backend.models import (
    InventoryDispatch,
    InventoryDispatchItem,
    InventoryRequest,
    InventoryRequestItem,
    Ticket,
    TicketAssignmentHistory,
    TicketAttachment,
    TicketAuditEvent,
    TicketComment,
    TicketStatus,
    TicketStatusTransition,
)


class TicketRepository:
    """Persist and query ticket aggregates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def save(self, ticket: Ticket) -> Ticket:
        self._session.add(ticket)
        self._session.commit()
        self._session.refresh(ticket)
        return self.get_ticket_detail(ticket.ticket_id) or ticket

    def _summary_options(self):
        return ()

    def _detail_options(self):
        return (
            selectinload(Ticket.comments).selectinload(TicketComment.attachments),
            selectinload(Ticket.attachments),
            selectinload(Ticket.status_history),
            selectinload(Ticket.assignment_history),
            selectinload(Ticket.audit_events),
            selectinload(Ticket.inventory_requests)
            .selectinload(InventoryRequest.items)
            .selectinload(InventoryRequestItem.product),
            selectinload(Ticket.inventory_requests)
            .selectinload(InventoryRequest.dispatches)
            .selectinload(InventoryDispatch.items)
            .selectinload(InventoryDispatchItem.product),
            selectinload(Ticket.dispatches)
            .selectinload(InventoryDispatch.items)
            .selectinload(InventoryDispatchItem.product),
        )

    def get_ticket_detail(self, ticket_id: str) -> Ticket | None:
        statement = select(Ticket).options(*self._detail_options()).where(Ticket.ticket_id == ticket_id)
        return self._session.scalar(statement)

    def get_attachment(self, attachment_id: str) -> TicketAttachment | None:
        return self._session.get(TicketAttachment, attachment_id)

    def list_tickets_assigned_to_user(self, crm_user_id: str) -> list[Ticket]:
        statement = (
            select(Ticket)
            .options(*self._summary_options())
            .where(Ticket.assigned_user_id == crm_user_id, Ticket.status != TicketStatus.CLOSED.value)
            .order_by(Ticket.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def list_unassigned_tickets_for_roles(self, role_ids: list[str]) -> list[Ticket]:
        if not role_ids:
            return []
        statement = (
            select(Ticket)
            .options(*self._summary_options())
            .where(
                Ticket.assigned_role_id.in_(role_ids),
                Ticket.assigned_user_id.is_(None),
                Ticket.status != TicketStatus.CLOSED.value,
            )
            .order_by(Ticket.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def list_tracking_tickets_for_roles(self, role_ids: list[str]) -> list[Ticket]:
        if not role_ids:
            return []
        statement = (
            select(Ticket)
            .options(*self._summary_options())
            .where(Ticket.assigned_role_id.in_(role_ids), Ticket.status != TicketStatus.CLOSED.value)
            .order_by(Ticket.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def list_tracking_tickets_for_all_roles(self) -> list[Ticket]:
        statement = (
            select(Ticket)
            .options(*self._summary_options())
            .where(Ticket.status != TicketStatus.CLOSED.value)
            .order_by(Ticket.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def list_closed_tickets(self) -> list[Ticket]:
        statement = (
            select(Ticket)
            .options(*self._summary_options())
            .where(Ticket.status == TicketStatus.CLOSED.value)
            .order_by(Ticket.closed_at.desc(), Ticket.updated_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def find_latest_ticket_number(self) -> str | None:
        statement = select(Ticket.ticket_number).order_by(Ticket.created_at.desc(), Ticket.ticket_number.desc()).limit(1)
        return self._session.scalar(statement)
