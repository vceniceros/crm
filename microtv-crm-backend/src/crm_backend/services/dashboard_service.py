"""Dashboard application service with role-aware summary aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select, true
from sqlalchemy.orm import Session, aliased

from crm_backend.models import Notification, Subtask, Task, TaskStatus, Ticket, TicketPriority, TicketStatus
from crm_backend.schemas.dashboard import (
    DashboardKpiResponse,
    DashboardRecentActivityResponse,
    DashboardRecentTicketResponse,
    DashboardSummaryResponse,
)
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class VisibilityScope:
    is_admin_or_executive: bool
    is_tecnico: bool
    is_deposito: bool
    role_keys: list[str]
    role_ids: list[str]
    actor_crm_user_id: str


class DashboardService:
    """Build dashboard metrics and lists from live DB data."""

    _OPERATIVE_SEGMENT_KEYS = {"tecnico", "deposito"}

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_dashboard_summary(self, actor: ResolvedCrmSession) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            page_title="Resumen operativo",
            page_subtitle=(
                "Seguimiento general de tickets, tareas y actividad reciente del equipo "
                "con datos reales de operación."
            ),
            kpis=self.get_kpis(actor),
            recent_tickets=self.get_recent_tickets(actor),
            recent_activity=self.get_recent_activity(actor),
        )

    def get_kpis(self, actor: ResolvedCrmSession) -> list[DashboardKpiResponse]:
        scope = self._build_scope(actor)
        now = datetime.now(UTC)
        week_start = self._start_of_week(now)
        prev_week_start = week_start - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        open_statuses = [
            TicketStatus.OPEN.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.PENDING_APPROVAL.value,
        ]
        open_tickets = self._count_tickets(
            scope,
            extra_conditions=[
                Ticket.deleted_at.is_(None),
                Ticket.status.in_(open_statuses),
            ],
        )
        current_week_open = self._count_tickets(
            scope,
            extra_conditions=[
                Ticket.deleted_at.is_(None),
                Ticket.status.in_(open_statuses),
                Ticket.created_at >= week_start,
                Ticket.created_at < now,
            ],
        )
        previous_week_open = self._count_tickets(
            scope,
            extra_conditions=[
                Ticket.deleted_at.is_(None),
                Ticket.status.in_(open_statuses),
                Ticket.created_at >= prev_week_start,
                Ticket.created_at < week_start,
            ],
        )
        weekly_delta = current_week_open - previous_week_open

        tasks_in_progress = self._count_tasks(
            scope,
            extra_conditions=[
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.IN_PROGRESS.value,
            ],
        )
        completed_subtasks_month = (
            self._session.scalar(
                select(func.count())
                .select_from(Subtask)
                .join(Task, Subtask.task_id == Task.task_id)
                .where(
                    and_(
                        Task.deleted_at.is_(None),
                        self._task_visibility_condition(scope),
                        Subtask.completed_at.is_not(None),
                        Subtask.completed_at >= month_start,
                        Subtask.completed_at < now,
                    )
                )
            )
            or 0
        )

        pending_external_tickets = self._count_tickets(
            scope,
            extra_conditions=[
                Ticket.deleted_at.is_(None),
                Ticket.status.in_([TicketStatus.ON_HOLD.value, TicketStatus.PENDING_APPROVAL.value]),
            ],
        )
        pending_external_tasks = self._count_tasks(
            scope,
            extra_conditions=[
                Task.deleted_at.is_(None),
                Task.status.in_([TaskStatus.BLOCKED.value, TaskStatus.PENDING_APPROVAL.value]),
            ],
        )
        pending_external = pending_external_tickets + pending_external_tasks

        closed_tickets_month = self._count_tickets(
            scope,
            extra_conditions=[
                Ticket.deleted_at.is_(None),
                Ticket.status == TicketStatus.CLOSED.value,
                Ticket.closed_at.is_not(None),
                Ticket.closed_at >= month_start,
                Ticket.closed_at < now,
            ],
        )
        closed_tasks_month = self._count_tasks(
            scope,
            extra_conditions=[
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED.value,
                Task.finalized_at.is_not(None),
                Task.finalized_at >= month_start,
                Task.finalized_at < now,
            ],
        )

        return [
            DashboardKpiResponse(
                key="open_tickets",
                label="Tickets Abiertos",
                value=open_tickets,
                secondary=self._format_delta_text(weekly_delta),
                variant="danger",
            ),
            DashboardKpiResponse(
                key="tasks_in_progress",
                label="Tareas en Progreso",
                value=tasks_in_progress,
                secondary=f"{completed_subtasks_month} subtareas completadas en el mes",
                variant="info",
            ),
            DashboardKpiResponse(
                key="pending_external",
                label="Pendientes externos",
                value=pending_external,
                secondary=(
                    f"{pending_external_tickets} tickets + {pending_external_tasks} tareas "
                    "bloqueadas/en aprobación"
                ),
                variant="warning",
            ),
            DashboardKpiResponse(
                key="closed_this_month",
                label="Cerradas (mes)",
                value=closed_tickets_month + closed_tasks_month,
                secondary=f"{closed_tickets_month} tickets + {closed_tasks_month} tareas",
                variant="success",
            ),
        ]

    def get_recent_tickets(self, actor: ResolvedCrmSession, limit: int = 4) -> list[DashboardRecentTicketResponse]:
        scope = self._build_scope(actor)
        statement = (
            select(Ticket)
            .where(
                Ticket.deleted_at.is_(None),
                self._ticket_visibility_condition(scope),
            )
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        tickets = list(self._session.scalars(statement).all())

        return [
            DashboardRecentTicketResponse(
                ticket_id=ticket.ticket_id,
                ticket_public_id=ticket.ticket_number,
                subject=ticket.title,
                client=ticket.client_name or "Sin cliente",
                priority=ticket.priority,
                priority_tone=self._map_priority_tone(ticket.priority),
                status=ticket.status,
                status_tone=self._map_status_tone(ticket.status),
                assigned_to=ticket.assigned_user_display_name or "Sin asignar",
                assigned_initials=self._resolve_initials(ticket.assigned_user_display_name),
                target_route=f"/tickets/{ticket.ticket_id}",
            )
            for ticket in tickets
        ]

    def get_recent_activity(self, actor: ResolvedCrmSession, limit: int = 6) -> list[DashboardRecentActivityResponse]:
        scope = self._build_scope(actor)
        statement = (
            select(Notification)
            .where(self._notification_visibility_condition(scope))
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        notifications = list(self._session.scalars(statement).all())

        return [self._map_notification_to_activity(notification) for notification in notifications]

    def _build_scope(self, actor: ResolvedCrmSession) -> VisibilityScope:
        normalized_actor_role_keys = [
            role_key
            for role_key in (self._normalize_role_key(role_key) for role_key in actor.role_keys)
            if role_key is not None
        ]
        role_keys = sorted(set(normalized_actor_role_keys))
        is_admin_or_executive = bool({"admin", "ejecutivo"}.intersection(role_keys))

        if is_admin_or_executive:
            scoped_role_keys = role_keys
        else:
            scoped_role_keys = [role_key for role_key in role_keys if role_key in self._OPERATIVE_SEGMENT_KEYS]
            if not scoped_role_keys:
                scoped_role_keys = role_keys

        role_ids = [
            assignment.crm_role_id
            for assignment in actor.crm_user.assigned_roles
            if assignment.crm_role_id is not None
            and (
                is_admin_or_executive
                or self._normalize_role_key(getattr(assignment.role, "role_key", None)) in scoped_role_keys
            )
        ]

        if not role_ids and not is_admin_or_executive:
            role_ids = [
                assignment.crm_role_id
                for assignment in actor.crm_user.assigned_roles
                if assignment.crm_role_id is not None
            ]

        return VisibilityScope(
            is_admin_or_executive=is_admin_or_executive,
            is_tecnico="tecnico" in scoped_role_keys,
            is_deposito="deposito" in scoped_role_keys,
            role_keys=scoped_role_keys,
            role_ids=role_ids,
            actor_crm_user_id=actor.crm_user.crm_user_id,
        )

    def _normalize_role_key(self, role_key: str | None) -> str | None:
        if not isinstance(role_key, str):
            return None
        normalized = role_key.strip().lower()
        if normalized == "admin_crm":
            return "admin"
        if normalized == "tecnico_campo":
            return "tecnico"
        if normalized == "encargado_deposito":
            return "deposito"
        return normalized or None

    def _ticket_visibility_condition(self, scope: VisibilityScope):
        if scope.is_admin_or_executive:
            return true()

        visible_conditions = [Ticket.assigned_user_id == scope.actor_crm_user_id]
        if scope.role_ids:
            visible_conditions.append(Ticket.assigned_role_id.in_(scope.role_ids))
        return or_(*visible_conditions)

    def _task_visibility_condition(self, scope: VisibilityScope):
        if scope.is_admin_or_executive:
            return true()

        visible_conditions = [Task.current_assigned_crm_user_id == scope.actor_crm_user_id]
        if scope.role_keys:
            subtask_alias = aliased(Subtask)
            visible_conditions.append(
                exists(
                    select(subtask_alias.subtask_id).where(
                        subtask_alias.task_id == Task.task_id,
                        subtask_alias.responsible_role_key.in_(scope.role_keys),
                    )
                )
            )
        return or_(*visible_conditions)

    def _notification_visibility_condition(self, scope: VisibilityScope):
        if scope.is_admin_or_executive:
            return true()
        if scope.is_deposito:
            return or_(
                Notification.recipient_crm_user_id == scope.actor_crm_user_id,
                Notification.notification_type.like("deposit_%"),
            )
        return Notification.recipient_crm_user_id == scope.actor_crm_user_id

    def _count_tickets(self, scope: VisibilityScope, *, extra_conditions: list[object]) -> int:
        statement = select(func.count()).select_from(Ticket).where(
            and_(
                self._ticket_visibility_condition(scope),
                *extra_conditions,
            )
        )
        return self._session.scalar(statement) or 0

    def _count_tasks(self, scope: VisibilityScope, *, extra_conditions: list[object]) -> int:
        statement = select(func.count()).select_from(Task).where(
            and_(
                self._task_visibility_condition(scope),
                *extra_conditions,
            )
        )
        return self._session.scalar(statement) or 0

    def _map_notification_to_activity(self, notification: Notification) -> DashboardRecentActivityResponse:
        entity_type = notification.entity_type
        target_route = self._build_activity_route(entity_type, notification.entity_id)
        actor_name = None
        if isinstance(notification.metadata_json, dict):
            metadata_actor = notification.metadata_json.get("actor_name")
            if isinstance(metadata_actor, str) and metadata_actor.strip():
                actor_name = metadata_actor.strip()

        return DashboardRecentActivityResponse(
            type=self._activity_type_label(entity_type),
            tone=self._activity_tone(notification.notification_type),
            text=notification.body or notification.title,
            timestamp=notification.created_at,
            actor=actor_name or "Sistema",
            target_entity_type=entity_type,
            target_entity_id=notification.entity_id,
            target_public_code=self._extract_public_code(notification),
            target_route=target_route,
        )

    def _build_activity_route(self, entity_type: str | None, entity_id: str | None) -> str | None:
        if not entity_type:
            return None
        if entity_type == "ticket" and entity_id:
            return f"/tickets/{entity_id}"
        if entity_type == "task" and entity_id:
            return f"/tasks/{entity_id}"
        if entity_type == "deposit_request":
            return "/inventory/requests"
        return None

    def _extract_public_code(self, notification: Notification) -> str | None:
        if not isinstance(notification.metadata_json, dict):
            return None
        for key in ("ticket_number", "task_number", "request_code", "public_code"):
            value = notification.metadata_json.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _format_delta_text(self, delta: int) -> str:
        if delta > 0:
            return f"+{delta} respecto de la semana anterior"
        if delta < 0:
            return f"{delta} respecto de la semana anterior"
        return "Sin cambios respecto de la semana anterior"

    def _map_priority_tone(self, priority: str) -> str:
        normalized = (priority or "").upper()
        if normalized == TicketPriority.CRITICAL.value:
            return "critical"
        if normalized == TicketPriority.HIGH.value:
            return "high"
        if normalized == TicketPriority.LOW.value:
            return "low"
        return "medium"

    def _map_status_tone(self, status: str) -> str:
        normalized = (status or "").upper()
        if normalized in {TicketStatus.OPEN.value, TicketStatus.PENDING_APPROVAL.value}:
            return "neutral"
        if normalized == TicketStatus.IN_PROGRESS.value:
            return "progress"
        if normalized == TicketStatus.ON_HOLD.value:
            return "warning"
        if normalized in {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}:
            return "success"
        return "neutral"

    def _activity_tone(self, notification_type: str) -> str:
        normalized = (notification_type or "").lower()
        if "rejected" in normalized:
            return "danger"
        if "approved" in normalized or "received" in normalized:
            return "success"
        if "deposit" in normalized or "pending" in normalized:
            return "warning"
        return "info"

    def _activity_type_label(self, entity_type: str | None) -> str:
        if entity_type == "ticket":
            return "Ticket"
        if entity_type == "task":
            return "Tarea"
        if entity_type == "deposit_request":
            return "Depósito"
        return "Sistema"

    def _resolve_initials(self, full_name: str | None) -> str:
        if not full_name:
            return "--"
        parts = [chunk for chunk in full_name.strip().split(" ") if chunk]
        if not parts:
            return "--"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return f"{parts[0][0]}{parts[1][0]}".upper()

    def _start_of_week(self, value: datetime) -> datetime:
        weekday = value.weekday()
        return (value - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
