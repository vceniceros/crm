"""Application service for CRM reporting aggregates."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
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
    Location,
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
from crm_backend.models.settings import CrmCategory
from crm_backend.schemas.reports import (
    CategoryResolutionReportResponse,
    CategoryResolutionReportSummary,
    CategoryResolutionRow,
    DepositRequestReportResponse,
    DepositRequestReportRow,
    DepositRequestReportSummary,
    ExecutivePerformanceResponse,
    ExecutivePerformanceRow,
    ExecutivePerformanceSummary,
    MyTaskReportResponse,
    MyTaskReportRow,
    MyTaskReportSummary,
    MyTicketReportResponse,
    MyTicketReportRow,
    MyTicketReportSummary,
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


@dataclass(slots=True)
class ExecutiveAggregate:
    group_key: str
    group_label: str
    primary_role: str | None = None
    total_assigned: int = 0
    closed_count: int = 0
    rejected_count: int = 0
    close_hours: list[float] = field(default_factory=list)
    total_comments: int = 0


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

    def list_location_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        _ = actor
        locations = list(
            self._session.scalars(
                select(Location)
                .order_by(Location.address_label.asc(), Location.formatted_address.asc(), Location.location_id.asc())
            ).all()
        )
        return [
            ReportOptionItem(id=location.location_id, label=self._location_label(location) or location.location_id)
            for location in locations
        ]

    def list_role_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        self._ensure_can_view_executive(actor)
        roles = list(
            self._session.scalars(
                select(CrmRole)
                .where(CrmRole.is_active.is_(True))
                .order_by(CrmRole.role_label.asc(), CrmRole.role_key.asc())
            ).all()
        )
        options: dict[str, ReportOptionItem] = {}
        for role in roles:
            normalized = self._normalize_role_key(role.role_key)
            if normalized is None:
                continue
            if normalized not in {"admin", "ejecutivo", "tecnico", "deposito"}:
                continue
            options.setdefault(
                normalized,
                ReportOptionItem(id=normalized, label=role.role_label or normalized.title()),
            )
        return sorted(options.values(), key=lambda option: option.label)

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

    def my_tickets_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        category_id: str | None,
        priority: str | None,
        client_id: str | None,
        location_id: str | None,
        group_by: str,
    ) -> MyTicketReportResponse:
        query = (
            select(Ticket)
            .where(Ticket.deleted_at.is_(None))
            .where(
                or_(
                    Ticket.assigned_user_id == actor.crm_user.crm_user_id,
                    Ticket.created_by_crm_user_id == actor.crm_user.crm_user_id,
                )
            )
        )
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(Ticket.created_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(Ticket.created_at <= range_filter.end)
        if category_id:
            query = query.where(Ticket.category_id == category_id)
        if priority:
            query = query.where(Ticket.priority == priority)
        if client_id:
            query = query.where(Ticket.client_id == client_id)
        if location_id:
            query = query.where(Ticket.location_id == location_id)

        tickets = list(self._session.scalars(query.order_by(Ticket.created_at.desc())).all())
        resolution_hours = [
            self._ticket_resolution_hours(ticket)
            for ticket in tickets
            if self._ticket_resolution_hours(ticket) is not None
        ]
        resolved_count = sum(1 for ticket in tickets if ticket.status in {"RESOLVED", "CLOSED"})
        closed_count = sum(1 for ticket in tickets if ticket.status == "CLOSED")
        open_count = sum(1 for ticket in tickets if ticket.status in {"OPEN", "IN_PROGRESS", "ON_HOLD", "PENDING_APPROVAL"})

        summary = MyTicketReportSummary(
            total=len(tickets),
            resolved=resolved_count,
            closed=closed_count,
            open=open_count,
            avg_resolution_hours=round(mean(resolution_hours), 2) if resolution_hours else None,
            min_resolution_hours=round(min(resolution_hours), 2) if resolution_hours else None,
            max_resolution_hours=round(max(resolution_hours), 2) if resolution_hours else None,
            resolution_rate=round((resolved_count / len(tickets)) * 100, 2) if tickets else 0,
        )
        rows = [
            MyTicketReportRow(
                ticket_number=ticket.ticket_number,
                title=ticket.title,
                status=ticket.status,
                priority=ticket.priority,
                category=ticket.category_name,
                client=ticket.client_name,
                location=self._location_label(ticket.location),
                created_at=ticket.created_at,
                resolution_hours=self._ticket_resolution_hours(ticket),
            )
            for ticket in tickets
        ]

        return MyTicketReportResponse(
            chart_kind=self._my_ticket_chart_kind(group_by),
            summary=summary,
            kpis=self._my_ticket_kpis(summary),
            series=self._build_my_ticket_series(tickets, group_by),
            rows=rows,
        )

    def my_tasks_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        category_id: str | None,
        priority: str | None,
        client_id: str | None,
        group_by: str,
    ) -> MyTaskReportResponse:
        query = (
            select(Task)
            .where(Task.deleted_at.is_(None))
            .where(Task.current_assigned_crm_user_id == actor.crm_user.crm_user_id)
        )
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(Task.created_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(Task.created_at <= range_filter.end)
        if category_id:
            query = query.where(Task.category_id == category_id)
        if priority:
            query = query.where(Task.priority == priority)
        if client_id:
            query = query.where(Task.client_id == client_id)

        tasks = list(self._session.scalars(query.order_by(Task.created_at.desc())).all())
        completion_hours = [
            self._task_completion_hours(task)
            for task in tasks
            if self._task_completion_hours(task) is not None
        ]
        completed_count = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED.value)
        blocked_count = sum(1 for task in tasks if task.status == TaskStatus.BLOCKED.value)
        pending_count = len(tasks) - completed_count - blocked_count

        summary = MyTaskReportSummary(
            total=len(tasks),
            completed=completed_count,
            pending=pending_count,
            blocked=blocked_count,
            avg_completion_hours=round(mean(completion_hours), 2) if completion_hours else None,
            min_completion_hours=round(min(completion_hours), 2) if completion_hours else None,
            max_completion_hours=round(max(completion_hours), 2) if completion_hours else None,
            completion_rate=round((completed_count / len(tasks)) * 100, 2) if tasks else 0,
        )
        rows = [
            MyTaskReportRow(
                task_code=self._visible_task_code(task.task_id),
                title=task.task_title,
                status=task.status,
                priority=task.priority,
                category=task.category_name,
                client=task.client_name,
                created_at=task.created_at,
                completion_hours=self._task_completion_hours(task),
            )
            for task in tasks
        ]

        return MyTaskReportResponse(
            chart_kind=self._my_task_chart_kind(group_by),
            summary=summary,
            kpis=self._my_task_kpis(summary),
            series=self._build_my_task_series(tasks, group_by),
            rows=rows,
        )

    def executive_performance_report(
        self,
        actor: ResolvedCrmSession,
        *,
        date_from: date | None,
        date_to: date | None,
        group_by: str,
        category_id: str | None,
        priority: str | None,
        client_id: str | None,
        role_key: str | None,
        user_id: str | None,
    ) -> ExecutivePerformanceResponse:
        self._ensure_can_view_executive(actor)

        query = select(Ticket).where(Ticket.deleted_at.is_(None))
        range_filter = self._to_datetime_range(date_from, date_to)
        if range_filter.start is not None:
            query = query.where(Ticket.created_at >= range_filter.start)
        if range_filter.end is not None:
            query = query.where(Ticket.created_at <= range_filter.end)
        if category_id:
            query = query.where(Ticket.category_id == category_id)
        if priority:
            query = query.where(Ticket.priority == priority)
        if client_id:
            query = query.where(Ticket.client_id == client_id)
        if user_id:
            query = query.where(Ticket.assigned_user_id == user_id)

        tickets = list(self._session.scalars(query.order_by(Ticket.created_at.desc())).all())
        normalized_role = self._normalize_role_key(role_key)
        if normalized_role:
            tickets = [ticket for ticket in tickets if self._ticket_matches_role_filter(ticket, normalized_role)]

        aggregates: dict[str, ExecutiveAggregate] = {}
        all_close_hours: list[float] = []
        for ticket in tickets:
            group_key, group_label, primary_role = self._executive_grouping(ticket, group_by)
            aggregate = aggregates.setdefault(
                group_key,
                ExecutiveAggregate(group_key=group_key, group_label=group_label, primary_role=primary_role),
            )
            aggregate.total_assigned += 1
            aggregate.primary_role = aggregate.primary_role or primary_role
            if ticket.closed_at is not None:
                aggregate.closed_count += 1
                close_hours = (ticket.closed_at - ticket.created_at).total_seconds() / 3600
                aggregate.close_hours.append(close_hours)
                all_close_hours.append(close_hours)
            aggregate.total_comments += len(ticket.comments)
            aggregate.rejected_count += self._ticket_rejection_count(ticket)

        rows = [
            ExecutivePerformanceRow(
                group_key=aggregate.group_key,
                group_label=aggregate.group_label,
                primary_role=aggregate.primary_role,
                total_assigned=aggregate.total_assigned,
                closed_count=aggregate.closed_count,
                rejected_count=aggregate.rejected_count,
                avg_close_hours=round(mean(aggregate.close_hours), 2) if aggregate.close_hours else None,
                min_close_hours=round(min(aggregate.close_hours), 2) if aggregate.close_hours else None,
                max_close_hours=round(max(aggregate.close_hours), 2) if aggregate.close_hours else None,
                total_comments=aggregate.total_comments,
                avg_comments_per_ticket=round(aggregate.total_comments / aggregate.total_assigned, 2)
                if aggregate.total_assigned
                else None,
            )
            for aggregate in aggregates.values()
        ]
        rows.sort(
            key=lambda row: (
                row.avg_close_hours is None,
                row.avg_close_hours if row.avg_close_hours is not None else float("inf"),
                row.group_label,
            )
        )

        performers = [row for row in rows if row.avg_close_hours is not None]
        summary = ExecutivePerformanceSummary(
            total=len(tickets),
            total_groups=len(rows),
            overall_avg_close_hours=round(mean(all_close_hours), 2) if all_close_hours else None,
            best_performer=performers[0].group_label if performers else None,
            worst_performer=performers[-1].group_label if performers else None,
        )

        return ExecutivePerformanceResponse(
            summary=summary,
            kpis=self._executive_kpis(summary),
            series=self._build_executive_series(rows),
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

    def _ticket_resolution_hours(self, ticket: Ticket) -> float | None:
        finished_at = ticket.resolved_at or ticket.closed_at
        if finished_at is None:
            return None
        return round((finished_at - ticket.created_at).total_seconds() / 3600, 2)

    def _task_completion_hours(self, task: Task) -> float | None:
        if task.finalized_at is None:
            return None
        return round((task.finalized_at - task.created_at).total_seconds() / 3600, 2)

    def _my_ticket_chart_kind(self, group_by: str) -> str:
        if group_by == "priority":
            return "donut"
        if group_by == "time-series":
            return "area"
        if group_by == "status":
            return "bar"
        return "horizontal_bar"

    def _my_task_chart_kind(self, group_by: str) -> str:
        if group_by == "time-series":
            return "area"
        if group_by == "status":
            return "bar"
        return "horizontal_bar"

    def _build_my_ticket_series(self, tickets: list[Ticket], group_by: str) -> list[ReportSeriesPoint]:
        if group_by == "time-series":
            bucket: dict[str, int] = defaultdict(int)
            for ticket in tickets:
                bucket[ticket.created_at.date().isoformat()] += 1
            return [ReportSeriesPoint(label="Tickets", date=day, value=value) for day, value in sorted(bucket.items())]

        bucket: dict[str, int] = defaultdict(int)
        for ticket in tickets:
            if group_by == "status":
                key = ticket.status
                label = self._status_label(key)
            elif group_by == "priority":
                key = ticket.priority
                label = self._priority_label(key)
            elif group_by == "category":
                key = ticket.category_id or "__uncategorized__"
                label = ticket.category_name or "Sin categoría"
            elif group_by == "client":
                key = ticket.client_id
                label = ticket.client_name
            elif group_by == "location":
                key = ticket.location_id
                label = self._location_label(ticket.location) or "Sin ubicación"
            else:
                key = ticket.status
                label = self._status_label(ticket.status)
            bucket[f"{key}::{label}"] += 1

        ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
        return [
            ReportSeriesPoint(label=item.split("::", 1)[1], date=item.split("::", 1)[1], value=value)
            for item, value in ordered
        ]

    def _build_my_task_series(self, tasks: list[Task], group_by: str) -> list[ReportSeriesPoint]:
        if group_by == "time-series":
            bucket: dict[str, int] = defaultdict(int)
            for task in tasks:
                bucket[task.created_at.date().isoformat()] += 1
            return [ReportSeriesPoint(label="Tareas", date=day, value=value) for day, value in sorted(bucket.items())]

        bucket: dict[str, int] = defaultdict(int)
        for task in tasks:
            if group_by == "status":
                key = task.status
                label = self._status_label(key)
            elif group_by == "category":
                key = task.category_id or "__uncategorized__"
                label = task.category_name or "Sin categoría"
            elif group_by == "client":
                key = task.client_id
                label = task.client_name
            else:
                key = task.status
                label = self._status_label(task.status)
            bucket[f"{key}::{label}"] += 1

        ordered = sorted(bucket.items(), key=lambda item: (-item[1], item[0]))
        return [
            ReportSeriesPoint(label=item.split("::", 1)[1], date=item.split("::", 1)[1], value=value)
            for item, value in ordered
        ]

    def _my_ticket_kpis(self, summary: MyTicketReportSummary) -> list[ReportKpiItem]:
        return [
            ReportKpiItem(key="total", label="Total", value=summary.total),
            ReportKpiItem(key="resolved", label="Resueltos", value=summary.resolved),
            ReportKpiItem(key="closed", label="Cerrados", value=summary.closed),
            ReportKpiItem(key="open", label="Abiertos", value=summary.open),
            ReportKpiItem(key="avg_resolution_hours", label="Promedio resolución (h)", value=summary.avg_resolution_hours if summary.avg_resolution_hours is not None else "N/D"),
            ReportKpiItem(key="min_resolution_hours", label="Mínimo resolución (h)", value=summary.min_resolution_hours if summary.min_resolution_hours is not None else "N/D"),
            ReportKpiItem(key="max_resolution_hours", label="Máximo resolución (h)", value=summary.max_resolution_hours if summary.max_resolution_hours is not None else "N/D"),
            ReportKpiItem(key="resolution_rate", label="Tasa resolución (%)", value=summary.resolution_rate),
        ]

    def _my_task_kpis(self, summary: MyTaskReportSummary) -> list[ReportKpiItem]:
        return [
            ReportKpiItem(key="total", label="Total", value=summary.total),
            ReportKpiItem(key="completed", label="Completadas", value=summary.completed),
            ReportKpiItem(key="pending", label="Pendientes", value=summary.pending),
            ReportKpiItem(key="blocked", label="Bloqueadas", value=summary.blocked),
            ReportKpiItem(key="avg_completion_hours", label="Promedio cierre (h)", value=summary.avg_completion_hours if summary.avg_completion_hours is not None else "N/D"),
            ReportKpiItem(key="min_completion_hours", label="Mínimo cierre (h)", value=summary.min_completion_hours if summary.min_completion_hours is not None else "N/D"),
            ReportKpiItem(key="max_completion_hours", label="Máximo cierre (h)", value=summary.max_completion_hours if summary.max_completion_hours is not None else "N/D"),
            ReportKpiItem(key="completion_rate", label="Tasa cierre (%)", value=summary.completion_rate),
        ]

    def _executive_kpis(self, summary: ExecutivePerformanceSummary) -> list[ReportKpiItem]:
        return [
            ReportKpiItem(key="total_groups", label="Grupos analizados", value=summary.total_groups),
            ReportKpiItem(key="overall_avg_close_hours", label="Promedio global cierre (h)", value=summary.overall_avg_close_hours if summary.overall_avg_close_hours is not None else "N/D"),
            ReportKpiItem(key="best_performer", label="Mejor desempeño", value=summary.best_performer or "N/D"),
            ReportKpiItem(key="worst_performer", label="Peor desempeño", value=summary.worst_performer or "N/D"),
        ]

    def _executive_grouping(self, ticket: Ticket, group_by: str) -> tuple[str, str, str | None]:
        primary_role = self._ticket_primary_role(ticket)
        if group_by == "role":
            key = primary_role or self._normalize_role_key(ticket.assigned_role_key) or "__unassigned__"
            return key, self._role_label_from_key(key), primary_role
        if group_by == "category":
            key = ticket.category_id or "__uncategorized__"
            return key, ticket.category_name or "Sin categoría", primary_role
        if group_by == "priority":
            key = ticket.priority or "__no_priority__"
            return key, self._priority_label(key), primary_role
        if group_by == "client":
            key = ticket.client_id or "__no_client__"
            return key, ticket.client_name or "Sin cliente", primary_role
        user_key = ticket.assigned_user_id or "__unassigned__"
        return user_key, ticket.assigned_user_display_name or "Sin asignar", primary_role

    def _build_executive_series(self, rows: list[ExecutivePerformanceRow]) -> list[ReportSeriesPoint]:
        return [
            ReportSeriesPoint(label=row.group_label, date=row.group_label, value=row.avg_close_hours or 0)
            for row in rows
        ]

    def _ticket_rejection_count(self, ticket: Ticket) -> int:
        total = 0
        for event in ticket.audit_events:
            if event.event_type == "ticket.rejected_by_executive":
                total += 1
                continue
            from_status = str(event.payload_json.get("from_status") or "")
            to_status = str(event.payload_json.get("to_status") or "")
            if from_status == "PENDING_APPROVAL" and to_status in {"OPEN", "IN_PROGRESS"}:
                total += 1
        return total

    def _ticket_primary_role(self, ticket: Ticket) -> str | None:
        if ticket.assigned_user and ticket.assigned_user.assigned_roles:
            for assignment in ticket.assigned_user.assigned_roles:
                normalized = self._normalize_role_key(getattr(getattr(assignment, "role", None), "role_key", None))
                if normalized in {"admin", "ejecutivo", "tecnico", "deposito"}:
                    return normalized
        return self._normalize_role_key(ticket.assigned_role_key)

    def _ticket_matches_role_filter(self, ticket: Ticket, role_key: str) -> bool:
        if self._ticket_primary_role(ticket) == role_key:
            return True
        if ticket.assigned_user is None:
            return False
        return any(
            self._normalize_role_key(getattr(getattr(assignment, "role", None), "role_key", None)) == role_key
            for assignment in ticket.assigned_user.assigned_roles
        )

    def _ensure_can_view_executive(self, actor: ResolvedCrmSession) -> None:
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise PermissionError("La operación requiere rol administrador o ejecutivo.")

    def _normalize_role_key(self, role_key: str | None) -> str | None:
        if not isinstance(role_key, str):
            return None
        normalized = role_key.strip()
        if normalized == "admin_crm":
            return "admin"
        if normalized == "tecnico_campo":
            return "tecnico"
        if normalized == "encargado_deposito":
            return "deposito"
        return normalized or None

    def _role_label_from_key(self, role_key: str) -> str:
        if role_key == "admin":
            return "Administrador"
        if role_key == "ejecutivo":
            return "Ejecutivo"
        if role_key == "tecnico":
            return "Técnico"
        if role_key == "deposito":
            return "Depósito"
        if role_key == "__unassigned__":
            return "Sin asignar"
        return role_key

    def _location_label(self, location: Location | None) -> str | None:
        if location is None:
            return None
        if location.address_label:
            return location.address_label
        if location.formatted_address:
            return location.formatted_address
        return None

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

    def category_resolution_time_report(
        self,
        actor: ResolvedCrmSession,
        date_from: date | None = None,
        date_to: date | None = None,
        category_type: str | None = None,
    ) -> CategoryResolutionReportResponse:
        """Returns average ticket resolution time grouped by operational category."""
        if not {"admin", "ejecutivo"}.intersection(actor.role_keys):
            raise PermissionError("La operación requiere rol administrador o ejecutivo.")

        dr = self._to_datetime_range(date_from, date_to)

        # Load all operational categories
        cat_query = select(CrmCategory).where(CrmCategory.is_active.is_(True))
        if category_type:
            cat_query = cat_query.where(CrmCategory.category_type == category_type)
        categories = list(self._session.scalars(cat_query.order_by(CrmCategory.name.asc())).all())

        # Load closed tickets with a category in the date range
        ticket_query = (
            select(Ticket)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.closed_at.isnot(None))
            .where(Ticket.category_id.isnot(None))
        )
        if dr.start:
            ticket_query = ticket_query.where(Ticket.created_at >= dr.start)
        if dr.end:
            ticket_query = ticket_query.where(Ticket.created_at <= dr.end)
        tickets = list(self._session.scalars(ticket_query).all())

        # Also count ALL tickets (open/closed) per category for the total
        all_ticket_query = (
            select(Ticket)
            .where(Ticket.deleted_at.is_(None))
            .where(Ticket.category_id.isnot(None))
        )
        if dr.start:
            all_ticket_query = all_ticket_query.where(Ticket.created_at >= dr.start)
        if dr.end:
            all_ticket_query = all_ticket_query.where(Ticket.created_at <= dr.end)
        all_tickets = list(self._session.scalars(all_ticket_query).all())

        # Index by category_id
        cat_map = {cat.category_id: cat for cat in categories}
        closed_per_cat: dict[str, list[float]] = defaultdict(list)
        total_per_cat: dict[str, int] = defaultdict(int)

        for ticket in tickets:
            if ticket.category_id and ticket.closed_at and ticket.created_at:
                delta = ticket.closed_at - ticket.created_at
                hours = delta.total_seconds() / 3600
                closed_per_cat[ticket.category_id].append(hours)

        for ticket in all_tickets:
            if ticket.category_id:
                total_per_cat[ticket.category_id] += 1

        rows: list[CategoryResolutionRow] = []
        all_resolution_hours: list[float] = []
        for cat in categories:
            cid = cat.category_id
            resolution_hours = closed_per_cat.get(cid, [])
            all_resolution_hours.extend(resolution_hours)
            avg = mean(resolution_hours) if resolution_hours else None
            rows.append(
                CategoryResolutionRow(
                    category_id=cid,
                    category_name=cat.name,
                    total_tickets=total_per_cat.get(cid, 0),
                    closed_tickets=len(resolution_hours),
                    avg_resolution_hours=round(avg, 2) if avg is not None else None,
                    min_resolution_hours=round(min(resolution_hours), 2) if resolution_hours else None,
                    max_resolution_hours=round(max(resolution_hours), 2) if resolution_hours else None,
                )
            )

        # Add unassigned category row if there are tickets without category
        uncategorized = [t for t in all_tickets if t.category_id is None or t.category_id not in cat_map]
        if uncategorized:
            unc_closed = [t for t in uncategorized if t.closed_at and t.created_at]
            unc_hours = [(t.closed_at - t.created_at).total_seconds() / 3600 for t in unc_closed]  # type: ignore[operator]
            all_resolution_hours.extend(unc_hours)
            avg_unc = mean(unc_hours) if unc_hours else None
            rows.append(
                CategoryResolutionRow(
                    category_id="__uncategorized__",
                    category_name="Sin categoría",
                    total_tickets=len(uncategorized),
                    closed_tickets=len(unc_closed),
                    avg_resolution_hours=round(avg_unc, 2) if avg_unc is not None else None,
                    min_resolution_hours=round(min(unc_hours), 2) if unc_hours else None,
                    max_resolution_hours=round(max(unc_hours), 2) if unc_hours else None,
                )
            )

        rows.sort(key=lambda r: (r.avg_resolution_hours is None, r.avg_resolution_hours or 0))

        overall_avg = round(mean(all_resolution_hours), 2) if all_resolution_hours else None
        summary = CategoryResolutionReportSummary(
            total_categories=len(categories),
            total_tickets=sum(r.total_tickets for r in rows),
            overall_avg_resolution_hours=overall_avg,
        )

        series = [
            ReportSeriesPoint(
                label=row.category_name,
                date=row.category_name,
                value=row.avg_resolution_hours or 0,
                meta={"total": row.total_tickets, "closed": row.closed_tickets},
            )
            for row in rows
            if row.avg_resolution_hours is not None
        ]

        return CategoryResolutionReportResponse(
            chart_kind="horizontal_bar",
            summary=summary,
            kpis=[
                ReportKpiItem(key="total_categories", label="Categorías", value=summary.total_categories),
                ReportKpiItem(key="total_tickets", label="Tickets totales", value=summary.total_tickets),
                ReportKpiItem(
                    key="overall_avg_hours",
                    label="Prom. resolución global (hs)",
                    value=overall_avg if overall_avg is not None else "N/D",
                ),
            ],
            series=series,
            rows=rows,
        )

    def list_operational_category_options(self, actor: ResolvedCrmSession) -> list[ReportOptionItem]:
        """Returns active CRM operational categories for report filters."""
        _ = actor
        categories = list(
            self._session.scalars(
                select(CrmCategory)
                .where(CrmCategory.is_active.is_(True))
                .order_by(CrmCategory.name.asc())
            ).all()
        )
        return [ReportOptionItem(id=cat.category_id, label=cat.name) for cat in categories]
