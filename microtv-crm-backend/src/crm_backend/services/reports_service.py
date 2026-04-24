"""Application service for CRM reporting aggregates."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from crm_backend.models import (
    Client,
    CrmRole,
    CrmUser,
    CrmUserRole,
    InventoryDispatch,
    InventoryRequest,
    StockLevel,
    StockCategory,
    StockProduct,
    Subtask,
    Task,
    TaskAuditEvent,
    TaskStatus,
    Ticket,
    TicketAuditEvent,
    Warehouse,
)
from crm_backend.schemas.reports import (
    DepositRequestReportResponse,
    DepositRequestReportRow,
    DepositRequestReportSummary,
    ReportKpiItem,
    ReportOptionItem,
    ReportSeriesPoint,
    StockCriticalReportResponse,
    StockCriticalReportRow,
    StockCriticalReportSummary,
    TaskReportResponse,
    TaskReportRow,
    TaskReportSummary,
    TicketReportResponse,
    TicketReportRow,
    TicketReportSummary,
    UserActivityReportResponse,
    UserActivityReportRow,
    UserActivityReportSummary,
)
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class DateRange:
    start: datetime | None
    end: datetime | None


class ReportsService:
    """Builds report payloads for dashboard-like analytics pages."""

    ACTION_TYPE_LABELS = {
        "ticket.created": "Ticket creado",
        "ticket.assignment_changed": "Asignación de ticket modificada",
        "ticket.pending_executive_approval": "Ticket pendiente de aprobación ejecutiva",
        "ticket.closed": "Ticket cerrado",
        "ticket.approved_by_executive": "Ticket aprobado por ejecutivo",
        "ticket.rejected_by_executive": "Ticket rechazado por ejecutivo",
        "subtask.assigned_manually": "Tarea asignada",
        "subtask.claimed": "Tarea tomada por técnico",
        "subtask.closed": "Tarea cerrada",
        "task.approved_by_executive": "Tarea aprobada por ejecutivo",
        "task.rejected_by_executive": "Tarea rechazada por ejecutivo",
        "request.created": "Solicitud a depósito creada",
        "request.reviewed": "Solicitud a depósito autorizada",
        "request.dispatched": "Solicitud a depósito despachada",
    }

    STATUS_LABELS = {
        "OPEN": "Abierto",
        "IN_PROGRESS": "En progreso",
        "ON_HOLD": "Bloqueado",
        "PENDING_APPROVAL": "Pendiente",
        "RESOLVED": "Resuelto",
        "CLOSED": "Cerrado",
        "PENDING": "Pendiente",
        "PENDING_DISPATCH": "Pendiente de despacho",
        "PENDING_RECEIPT": "Pendiente de recepción",
        "APPROVED": "Autorizado",
        "COMPLETED": "Completado",
        "REJECTED": "Rechazado",
        "CANCELLED": "Cancelado",
        "BLOCKED": "Bloqueado",
        "SIN_STOCK": "Sin stock",
        "BAJO_MINIMO": "Bajo mínimo",
        "OK": "OK",
    }

    PRIORITY_LABELS = {
        "LOW": "Baja",
        "MEDIUM": "Media",
        "HIGH": "Alta",
        "CRITICAL": "Crítica",
    }

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_user_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            users = list(
                self._session.scalars(
                    select(CrmUser)
                    .where(CrmUser.deleted_at.is_(None))
                    .where(CrmUser.is_active_in_crm.is_(True))
                    .order_by(CrmUser.display_name.asc(), CrmUser.email.asc(), CrmUser.crm_user_id.asc())
                ).all()
            )
        else:
            users = [actor.crm_user]

        return [
            ReportOptionItem(id=user.crm_user_id, label=user.display_name or user.email or user.crm_user_id)
            for user in users
        ]

    def list_client_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        _ = actor
        clients = list(
            self._session.scalars(
                select(Client)
                .where(Client.deleted_at.is_(None))
                .where(Client.is_active.is_(True))
                .order_by(Client.business_name.asc(), Client.client_id.asc())
            ).all()
        )
        return [ReportOptionItem(id=client.client_id, label=client.business_name) for client in clients]

    def list_category_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        self._ensure_can_view_stock(actor)
        categories = list(
            self._session.scalars(
                select(StockCategory)
                .where(StockCategory.is_active.is_(True))
                .order_by(StockCategory.category_name.asc(), StockCategory.category_id.asc())
            ).all()
        )
        return [ReportOptionItem(id=category.stock_category_id, label=category.name) for category in categories]

    def list_warehouse_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        self._ensure_can_view_stock(actor)
        warehouses = list(
            self._session.scalars(
                select(Warehouse)
                .where(Warehouse.is_active.is_(True))
                .order_by(Warehouse.warehouse_name.asc(), Warehouse.warehouse_id.asc())
            ).all()
        )
        return [ReportOptionItem(id=warehouse.warehouse_id, label=warehouse.warehouse_name) for warehouse in warehouses]

    def list_technician_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        _ = actor
        technicians = list(
            self._session.scalars(
                select(CrmUser)
                .join(CrmUserRole, CrmUserRole.crm_user_id == CrmUser.crm_user_id)
                .join(CrmRole, CrmRole.crm_role_id == CrmUserRole.crm_role_id)
                .where(CrmUser.deleted_at.is_(None))
                .where(CrmUser.is_active_in_crm.is_(True))
                .where(CrmRole.is_active.is_(True))
                .where(CrmRole.role_key == "tecnico_campo")
                .order_by(CrmUser.display_name.asc(), CrmUser.email.asc(), CrmUser.crm_user_id.asc())
            ).unique().all()
        )

        return [
            ReportOptionItem(id=user.crm_user_id, label=user.display_name or user.email or user.crm_user_id)
            for user in technicians
        ]

    def list_action_type_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        _ = actor
        return [
            ReportOptionItem(id=action_type, label=label)
            for action_type, label in sorted(self.ACTION_TYPE_LABELS.items(), key=lambda item: item[1])
        ]

    def tickets_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        group_by: str,
        status: str | None,
        priority: str | None,
        client_id: str | None,
    ) -> TicketReportResponse:
        query = self._visible_tickets_query(actor)
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(Ticket.created_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(Ticket.created_at <= range_filter.end)
        if status:
            query = query.where(Ticket.status == status)
        if priority:
            query = query.where(Ticket.priority == priority)
        if client_id:
            query = query.where(Ticket.client_id == client_id)

        tickets = list(self._session.scalars(query.order_by(Ticket.created_at.desc())).all())

        resolution_hours = [
            (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
            for ticket in tickets
            if ticket.resolved_at is not None
        ]
        summary = TicketReportSummary(
            total=len(tickets),
            open=sum(1 for ticket in tickets if ticket.status in {"OPEN", "IN_PROGRESS"}),
            closed=sum(1 for ticket in tickets if ticket.status == "CLOSED"),
            pending=sum(1 for ticket in tickets if ticket.status in {"ON_HOLD", "PENDING_APPROVAL"}),
            avg_resolution_hours=round(mean(resolution_hours), 2) if resolution_hours else None,
        )

        series = self._build_ticket_series(tickets, group_by)
        rows = [
            TicketReportRow(
                ticket_number=ticket.ticket_number,
                title=ticket.title,
                client=ticket.client_name,
                priority=ticket.priority,
                status=ticket.status,
                assigned_to=ticket.assigned_user_display_name,
                created_at=ticket.created_at,
                closed_at=ticket.closed_at,
            )
            for ticket in tickets
        ]

        return TicketReportResponse(
            chart_kind="donut" if group_by in {"status", "priority"} else "horizontal_bar",
            summary=summary,
            kpis=self._ticket_kpis(summary),
            series=series,
            rows=rows,
        )

    def tasks_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        group_by: str,
        technician_id: str | None,
        status: str | None,
    ) -> TaskReportResponse:
        query = self._visible_tasks_query(actor)
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(Task.created_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(Task.created_at <= range_filter.end)
        if technician_id:
            query = query.where(Task.current_assigned_crm_user_id == technician_id)
        if status:
            query = query.where(Task.status == status)

        tasks = list(self._session.scalars(query.order_by(Task.created_at.desc())).all())

        summary = TaskReportSummary(
            total=len(tasks),
            in_progress=sum(1 for task in tasks if task.status == "IN_PROGRESS"),
            closed=sum(1 for task in tasks if task.status == TaskStatus.COMPLETED.value),
            overdue=0,
            blocked=sum(1 for task in tasks if task.status == "BLOCKED"),
        )

        rows = [
            TaskReportRow(
                task_code=self._visible_task_code(task.task_id),
                title=task.task_title,
                status=task.status,
                technician=task.current_assigned_user_display_name,
                client=task.client_name,
                created_at=task.created_at,
                due_at=None,
                closed_at=task.finalized_at,
            )
            for task in tasks
        ]

        return TaskReportResponse(
            chart_kind="donut" if group_by == "status" else "horizontal_bar",
            summary=summary,
            kpis=self._task_kpis(summary),
            series=self._build_task_series(tasks, group_by),
            rows=rows,
        )

    def stock_critical_report(
        self,
        actor: ResolvedCrmSession,
        *,
        category: str | None,
        warehouse_id: str | None,
        only_critical: bool,
    ) -> StockCriticalReportResponse:
        self._ensure_can_view_stock(actor)

        query: Select[tuple[StockProduct]] = select(StockProduct)
        if category:
            query = query.where(StockProduct.category_id == category)

        products = list(self._session.scalars(query.order_by(StockProduct.product_name.asc())).all())
        rows: list[StockCriticalReportRow] = []
        stock_contexts: list[tuple[StockProduct, StockCriticalReportRow, list[StockLevel], float, float]] = []
        critical_total = 0
        without_stock = 0
        below_minimum = 0

        for product in products:
            relevant_levels = [
                level
                for level in product.stock_entries
                if warehouse_id is None or level.warehouse_id == warehouse_id
            ]
            current_stock = float(sum((level.quantity_available for level in relevant_levels), start=0))
            min_values = [float(level.minimum_stock) for level in relevant_levels if level.minimum_stock is not None]
            stock_minimum = max(min_values) if min_values else 0.0

            status_label = "OK"
            if current_stock <= 0:
                status_label = "SIN_STOCK"
                without_stock += 1
                critical_total += 1
            elif stock_minimum > 0 and current_stock < stock_minimum:
                status_label = "BAJO_MINIMO"
                below_minimum += 1
                critical_total += 1

            if only_critical and status_label == "OK":
                continue

            latest_update = max((level.updated_at for level in relevant_levels), default=product.updated_at)
            rows.append(
                StockCriticalReportRow(
                    sku=product.visible_product_code,
                    product=product.name,
                    category=product.category.name if product.category is not None else "Sin categoria",
                    stock_current=round(current_stock, 2),
                    stock_minimum=round(stock_minimum, 2),
                    status=status_label,
                    updated_at=latest_update,
                )
            )
            stock_contexts.append((product, rows[-1], relevant_levels, current_stock, stock_minimum))

        summary = StockCriticalReportSummary(
            total=critical_total if only_critical else len(rows),
            without_stock=without_stock,
            below_minimum=below_minimum,
            valued_stock=None,
        )

        series = self._build_stock_history_series(stock_contexts, warehouse_id=warehouse_id)

        return StockCriticalReportResponse(
            chart_kind="line",
            summary=summary,
            kpis=[
                ReportKpiItem(key="total", label="Total críticos", value=summary.total),
                ReportKpiItem(key="without_stock", label="Sin stock", value=summary.without_stock),
                ReportKpiItem(key="below_minimum", label="Bajo mínimo", value=summary.below_minimum),
                ReportKpiItem(key="visualized_products", label="Productos graficados", value=min(10, len({row.sku for row in rows}))),
            ],
            series=series,
            rows=rows,
        )

    def deposit_requests_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        status: str | None,
        requester: str | None,
        approver: str | None,
    ) -> DepositRequestReportResponse:
        query = self._visible_requests_query(actor)
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(InventoryRequest.requested_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(InventoryRequest.requested_at <= range_filter.end)
        if status:
            query = query.where(InventoryRequest.request_status == status)
        if requester:
            query = query.where(InventoryRequest.requested_by_crm_user_id == requester)
        if approver:
            query = query.where(InventoryRequest.reviewed_by_crm_user_id == approver)

        requests = list(self._session.scalars(query.order_by(InventoryRequest.requested_at.desc())).all())

        dispatched_count = 0
        dispatch_hours: list[float] = []
        rows: list[DepositRequestReportRow] = []

        for request in requests:
            first_dispatch = min(request.dispatches, key=lambda item: item.created_at) if request.dispatches else None
            if first_dispatch is not None:
                dispatched_count += 1
                dispatch_hours.append((first_dispatch.created_at - request.requested_at).total_seconds() / 3600)

            source = self._request_source_label(request)
            rows.append(
                DepositRequestReportRow(
                    request_number=self._visible_request_code(request.request_id),
                    source=source,
                    requester=request.requested_by_display_name,
                    status=request.request_status,
                    approved_by=request.reviewed_by_display_name,
                    dispatched_by=first_dispatch.dispatched_by_display_name if first_dispatch else None,
                    created_at=request.requested_at,
                    dispatched_at=first_dispatch.created_at if first_dispatch else None,
                )
            )

        summary = DepositRequestReportSummary(
            total=len(requests),
            pending=sum(1 for request in requests if request.request_status in {"PENDING", "PENDING_DISPATCH", "PENDING_RECEIPT"}),
            approved=sum(1 for request in requests if request.request_status in {"APPROVED", "PENDING_DISPATCH", "PENDING_RECEIPT", "COMPLETED"}),
            dispatched=dispatched_count,
            rejected=sum(1 for request in requests if request.request_status == "REJECTED"),
            avg_dispatch_hours=round(mean(dispatch_hours), 2) if dispatch_hours else None,
        )

        series = self._build_request_series(requests)
        return DepositRequestReportResponse(
            chart_kind="area",
            summary=summary,
            kpis=[
                ReportKpiItem(key="total", label="Total", value=summary.total),
                ReportKpiItem(key="pending", label="Pendientes", value=summary.pending),
                ReportKpiItem(key="approved", label="Autorizadas", value=summary.approved),
                ReportKpiItem(key="dispatched", label="Despachadas", value=summary.dispatched),
                ReportKpiItem(key="rejected", label="Rechazadas", value=summary.rejected),
            ],
            series=series,
            rows=rows,
        )

    def user_activity_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        user_id: str | None,
        action_type: str | None,
    ) -> UserActivityReportResponse:
        self._ensure_can_view_activity(actor, user_id)
        range_filter = self._to_datetime_range(date_from, date_to)

        ticket_events = list(self._session.scalars(select(TicketAuditEvent).order_by(TicketAuditEvent.created_at.desc())).all())
        task_events = list(self._session.scalars(select(TaskAuditEvent).order_by(TaskAuditEvent.created_at.desc())).all())
        requests = list(self._session.scalars(select(InventoryRequest).order_by(InventoryRequest.requested_at.desc())).all())
        dispatches = list(self._session.scalars(select(InventoryDispatch).order_by(InventoryDispatch.created_at.desc())).all())

        ticket_codes = {
            ticket.ticket_id: ticket.ticket_number
            for ticket in self._session.scalars(select(Ticket)).all()
        }
        users = {
            user.crm_user_id: (user.display_name or user.email or user.crm_user_id)
            for user in self._session.scalars(select(CrmUser)).all()
        }

        rows: list[UserActivityReportRow] = []

        for event in ticket_events:
            if not self._match_activity_filters(event.actor_crm_user_id, event.event_type, event.created_at, user_id, action_type, range_filter):
                continue
            entity_code = ticket_codes.get(event.ticket_id, self._visible_ticket_code(event.ticket_id))
            rows.append(
                UserActivityReportRow(
                    user=users.get(event.actor_crm_user_id, event.actor_crm_user_id),
                    action=event.event_type,
                    entity="ticket",
                    entity_code=entity_code,
                    date=event.created_at,
                    description=self._activity_description(event.event_type, entity_code),
                )
            )

        for event in task_events:
            if not self._match_activity_filters(event.actor_crm_user_id, event.event_type, event.created_at, user_id, action_type, range_filter):
                continue
            code = self._visible_task_code(event.task_id)
            rows.append(
                UserActivityReportRow(
                    user=users.get(event.actor_crm_user_id, event.actor_crm_user_id),
                    action=event.event_type,
                    entity="task",
                    entity_code=code,
                    date=event.created_at,
                    description=self._activity_description(event.event_type, code),
                )
            )

        for request in requests:
            if self._match_activity_filters(request.requested_by_crm_user_id, "request.created", request.requested_at, user_id, action_type, range_filter):
                code = self._visible_request_code(request.request_id)
                rows.append(
                    UserActivityReportRow(
                        user=users.get(request.requested_by_crm_user_id, request.requested_by_crm_user_id),
                        action="request.created",
                        entity="deposit_request",
                        entity_code=code,
                        date=request.requested_at,
                        description=self._activity_description("request.created", code),
                    )
                )
            if request.reviewed_by_crm_user_id and request.reviewed_at and self._match_activity_filters(
                request.reviewed_by_crm_user_id,
                "request.reviewed",
                request.reviewed_at,
                user_id,
                action_type,
                range_filter,
            ):
                code = self._visible_request_code(request.request_id)
                rows.append(
                    UserActivityReportRow(
                        user=users.get(request.reviewed_by_crm_user_id, request.reviewed_by_crm_user_id),
                        action="request.reviewed",
                        entity="deposit_request",
                        entity_code=code,
                        date=request.reviewed_at,
                        description=self._activity_description("request.reviewed", code),
                    )
                )

        for dispatch in dispatches:
            if not self._match_activity_filters(
                dispatch.dispatched_by_crm_user_id,
                "request.dispatched",
                dispatch.created_at,
                user_id,
                action_type,
                range_filter,
            ):
                continue
            code = self._visible_request_code(dispatch.request_id) if dispatch.request_id else self._visible_dispatch_code(dispatch.dispatch_id)
            rows.append(
                UserActivityReportRow(
                    user=users.get(dispatch.dispatched_by_crm_user_id, dispatch.dispatched_by_crm_user_id),
                    action="request.dispatched",
                    entity="deposit_dispatch",
                    entity_code=code,
                    date=dispatch.created_at,
                    description=self._activity_description("request.dispatched", code),
                )
            )

        rows.sort(key=lambda item: item.date, reverse=True)

        summary = UserActivityReportSummary(
            total=len(rows),
            tickets_created=sum(1 for row in rows if row.action == "ticket.created"),
            tickets_assigned=sum(1 for row in rows if row.action == "ticket.assignment_changed"),
            tickets_closed=sum(1 for row in rows if row.action in {"ticket.closed", "ticket.approved_by_executive"}),
            tasks_assigned=sum(1 for row in rows if row.action in {"subtask.assigned_manually", "subtask.claimed"}),
            tasks_closed=sum(1 for row in rows if row.action in {"subtask.closed", "task.approved_by_executive"}),
            requests_created=sum(1 for row in rows if row.action == "request.created"),
            requests_approved=sum(1 for row in rows if row.action == "request.reviewed"),
            requests_dispatched=sum(1 for row in rows if row.action == "request.dispatched"),
        )

        series = self._build_activity_series(rows)

        return UserActivityReportResponse(
            chart_kind="line",
            summary=summary,
            kpis=[
                ReportKpiItem(key="total", label="Total acciones", value=summary.total),
                ReportKpiItem(key="tickets_created", label="Tickets creados", value=summary.tickets_created),
                ReportKpiItem(key="tickets_assigned", label="Tickets asignados", value=summary.tickets_assigned),
                ReportKpiItem(key="tickets_closed", label="Tickets cerrados", value=summary.tickets_closed),
                ReportKpiItem(key="tasks_assigned", label="Tareas asignadas", value=summary.tasks_assigned),
                ReportKpiItem(key="tasks_closed", label="Tareas cerradas", value=summary.tasks_closed),
                ReportKpiItem(key="requests_created", label="Solicitudes creadas", value=summary.requests_created),
                ReportKpiItem(key="requests_approved", label="Solicitudes autorizadas", value=summary.requests_approved),
                ReportKpiItem(key="requests_dispatched", label="Solicitudes despachadas", value=summary.requests_dispatched),
            ],
            series=series,
            rows=rows,
        )

    def _visible_tickets_query(self, actor: ResolvedCrmSession) -> Select[tuple[Ticket]]:
        base = select(Ticket)
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return base

        role_ids = [assignment.crm_role_id for assignment in actor.crm_user.assigned_roles]
        role_clause = Ticket.assigned_role_id.in_(role_ids) if role_ids else Ticket.assigned_role_id.is_(None)
        return base.where(or_(Ticket.assigned_user_id == actor.crm_user.crm_user_id, role_clause))

    def _visible_tasks_query(self, actor: ResolvedCrmSession) -> Select[tuple[Task]]:
        base = select(Task)
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return base

        return (
            base.outerjoin(Subtask, Subtask.task_id == Task.task_id)
            .where(
                or_(
                    Task.current_assigned_crm_user_id == actor.crm_user.crm_user_id,
                    Subtask.responsible_role_key.in_(actor.role_keys),
                )
            )
            .distinct()
        )

    def _visible_requests_query(self, actor: ResolvedCrmSession) -> Select[tuple[InventoryRequest]]:
        base = select(InventoryRequest)
        if {"admin", "ejecutivo", "deposito"}.intersection(actor.role_keys):
            return base
        return base.where(InventoryRequest.requested_by_crm_user_id == actor.crm_user.crm_user_id)

    def _ensure_can_view_stock(self, actor: ResolvedCrmSession) -> None:
        if not {"admin", "ejecutivo", "deposito"}.intersection(actor.role_keys):
            raise PermissionError("La operación requiere rol administrador, ejecutivo o depósito.")

    def _ensure_can_view_activity(self, actor: ResolvedCrmSession, user_id: str | None) -> None:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return
        if user_id is None or user_id == actor.crm_user.crm_user_id:
            return
        raise PermissionError("La operación requiere rol administrador o ejecutivo para ver actividad global.")

    def _build_ticket_series(self, tickets: list[Ticket], group_by: str) -> list[ReportSeriesPoint]:
        if group_by in {"status", "priority"}:
            bucket: dict[str, int] = defaultdict(int)
            for ticket in tickets:
                key = ticket.status if group_by == "status" else ticket.priority
                bucket[key] += 1
            ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
            return [
                ReportSeriesPoint(
                    label=self._report_label_for_value(group_by, key),
                    date=self._report_label_for_value(group_by, key),
                    value=value,
                )
                for key, value in ordered
            ]

        if group_by == "client":
            bucket: dict[str, int] = defaultdict(int)
            for ticket in tickets:
                bucket[ticket.client_name or "Sin cliente"] += 1

            ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))[:10]
            return [ReportSeriesPoint(label="Tickets", date=client_name, value=value) for client_name, value in ordered]

        bucket: dict[tuple[str, str], int] = defaultdict(int)
        for ticket in tickets:
            day = ticket.created_at.date().isoformat()
            if group_by == "status":
                label = ticket.status
            elif group_by == "priority":
                label = ticket.priority
            elif group_by == "client":
                label = ticket.client_name
            else:
                label = "total"
            bucket[(label, day)] += 1

        return [
            ReportSeriesPoint(label=label, date=day, value=value)
            for (label, day), value in sorted(bucket.items(), key=lambda item: (item[0][1], item[0][0]))
        ]

    def _build_task_series(self, tasks: list[Task], group_by: str) -> list[ReportSeriesPoint]:
        if group_by == "status":
            bucket: dict[str, int] = defaultdict(int)
            for task in tasks:
                bucket[task.status] += 1

            ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
            return [
                ReportSeriesPoint(
                    label=self._status_label(task_status),
                    date=self._status_label(task_status),
                    value=value,
                )
                for task_status, value in ordered
            ]

        if group_by == "technician":
            bucket: dict[str, int] = defaultdict(int)
            for task in tasks:
                bucket[task.current_assigned_user_display_name or "Sin técnico"] += 1

            ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))[:10]
            return [ReportSeriesPoint(label="Tareas", date=technician_name, value=value) for technician_name, value in ordered]

        bucket: dict[tuple[str, str], int] = defaultdict(int)
        for task in tasks:
            day = task.created_at.date().isoformat()
            if group_by == "status":
                label = task.status
            elif group_by == "technician":
                label = task.current_assigned_user_display_name or "Sin técnico"
            else:
                label = "total"
            bucket[(label, day)] += 1

        return [
            ReportSeriesPoint(label=label, date=day, value=value)
            for (label, day), value in sorted(bucket.items(), key=lambda item: (item[0][1], item[0][0]))
        ]

    def _build_request_series(self, requests: list[InventoryRequest]) -> list[ReportSeriesPoint]:
        bucket: dict[tuple[str, str], int] = defaultdict(int)
        for request in requests:
            bucket[(request.request_status, request.requested_at.date().isoformat())] += 1

        return [
            ReportSeriesPoint(label=self._status_label(label), date=day, value=value)
            for (label, day), value in sorted(bucket.items(), key=lambda item: (item[0][1], item[0][0]))
        ]

    def _build_stock_history_series(
        self,
        stock_contexts: list[tuple[StockProduct, StockCriticalReportRow, list[StockLevel], float, float]],
        *,
        warehouse_id: str | None,
    ) -> list[ReportSeriesPoint]:
        end_day = datetime.now(UTC).date()
        start_day = end_day - timedelta(days=29)
        sortable_contexts = sorted(
            stock_contexts,
            key=lambda item: (
                0 if item[1].status == "SIN_STOCK" else 1,
                0 if item[1].status == "BAJO_MINIMO" else 1,
                item[3] - item[4],
                item[1].product,
            ),
        )
        top_contexts = sortable_contexts[:10]
        series: list[ReportSeriesPoint] = []

        for product, row, _, current_stock, stock_minimum in top_contexts:
            relevant_movements = [
                movement
                for movement in product.movements
                if warehouse_id is None or movement.warehouse_id == warehouse_id
            ]
            if not relevant_movements:
                continue

            deltas_by_day: dict[date, float] = defaultdict(float)
            for movement in relevant_movements:
                signed_quantity = float(movement.quantity)
                if movement.movement_type == "OUT":
                    signed_quantity *= -1
                deltas_by_day[movement.created_at.date()] += signed_quantity

            stock_at_end_of_day = float(current_stock)
            cursor_day = end_day
            while cursor_day >= start_day:
                series.append(
                    ReportSeriesPoint(
                        label=row.product,
                        date=cursor_day.isoformat(),
                        value=round(stock_at_end_of_day, 2),
                        meta={"minimum_stock": round(stock_minimum, 2), "status": row.status},
                    )
                )
                stock_at_end_of_day -= deltas_by_day.get(cursor_day, 0.0)
                cursor_day -= timedelta(days=1)

        return sorted(series, key=lambda item: (item.date, item.label))

    def _build_activity_series(self, rows: list[UserActivityReportRow]) -> list[ReportSeriesPoint]:
        bucket: dict[str, int] = defaultdict(int)
        for row in rows:
            bucket[row.date.date().isoformat()] += 1

        return [ReportSeriesPoint(label="acciones", date=day, value=value) for day, value in sorted(bucket.items())]

    def _to_datetime_range(self, date_from: date | None, date_to: date | None) -> DateRange:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC) if date_from else None
        end = datetime.combine(date_to, datetime.max.time(), tzinfo=UTC) if date_to else None
        return DateRange(start=start, end=end)

    def _ticket_kpis(self, summary: TicketReportSummary) -> list[ReportKpiItem]:
        return [
            ReportKpiItem(key="total", label="Total", value=summary.total),
            ReportKpiItem(key="closed", label="Resueltos/Cerrados", value=summary.closed),
            ReportKpiItem(key="pending", label="Pendientes", value=summary.pending),
            ReportKpiItem(
                key="avg_resolution_hours",
                label="Promedio resolución (h)",
                value=summary.avg_resolution_hours if summary.avg_resolution_hours is not None else "N/D",
            ),
        ]

    def _task_kpis(self, summary: TaskReportSummary) -> list[ReportKpiItem]:
        return [
            ReportKpiItem(key="total", label="Total", value=summary.total),
            ReportKpiItem(key="in_progress", label="En progreso", value=summary.in_progress),
            ReportKpiItem(key="closed", label="Cerradas", value=summary.closed),
            ReportKpiItem(key="blocked", label="Bloqueadas", value=summary.blocked),
        ]

    def _request_source_label(self, request: InventoryRequest) -> str:
        if request.source_type == "TICKET" and request.external_ticket_id:
            ticket_number = self._session.scalar(select(Ticket.ticket_number).where(Ticket.ticket_id == request.external_ticket_id))
            return ticket_number or self._visible_ticket_code(request.external_ticket_id)
        if request.source_type == "TASK" and request.task_id:
            return self._visible_task_code(request.task_id)
        return "Sin origen"

    def _match_activity_filters(
        self,
        actor_id: str,
        action: str,
        created_at: datetime,
        user_id: str | None,
        action_type: str | None,
        range_filter: DateRange,
    ) -> bool:
        if user_id and actor_id != user_id:
            return False
        if action_type and action_type.lower() not in action.lower():
            return False
        if range_filter.start and created_at < range_filter.start:
            return False
        if range_filter.end and created_at > range_filter.end:
            return False
        return True

    def _activity_description(self, action: str, entity_code: str) -> str:
        return f"{self._action_type_label(action)} sobre {entity_code}"

    def _status_label(self, value: str) -> str:
        return self.STATUS_LABELS.get(value, value.replace("_", " ").title())

    def _priority_label(self, value: str) -> str:
        return self.PRIORITY_LABELS.get(value, value.replace("_", " ").title())

    def _action_type_label(self, value: str) -> str:
        if value in self.ACTION_TYPE_LABELS:
            return self.ACTION_TYPE_LABELS[value]
        return value.replace(".", " ").replace("_", " ").title()

    def _report_label_for_value(self, group_by: str, value: str) -> str:
        if group_by == "status":
            return self._status_label(value)
        if group_by == "priority":
            return self._priority_label(value)
        return value

    def _visible_task_code(self, task_id: str) -> str:
        return f"TSK-{task_id[:8].upper()}"

    def _visible_ticket_code(self, ticket_id: str) -> str:
        return f"TKT-{ticket_id[:8].upper()}"

    def _visible_request_code(self, request_id: str) -> str:
        return f"REQ-{request_id[:8].upper()}"

    def _visible_dispatch_code(self, dispatch_id: str) -> str:
        return f"DSP-{dispatch_id[:8].upper()}"
