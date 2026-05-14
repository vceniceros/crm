"""Application services for the ticket module."""

from __future__ import annotations

import re
import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select, text

from crm_backend.core.exceptions import (
    InvalidTaskAttachmentError,
    TaskAttachmentNotFoundError,
    TicketAccessDeniedError,
    TicketConflictError,
    TicketNotFoundError,
    TicketValidationError,
)
from crm_backend.infrastructure.task_media_storage import StoredTaskMedia, TaskMediaStorageFacade
from crm_backend.models import (
    CrmRole,
    CrmUser,
    NotificationRule,
    StockProduct,
    Ticket,
    TicketAssignmentHistory,
    TicketAttachment,
    TicketAttachmentType,
    TicketAuditEvent,
    TicketComment,
    TicketCommentMention,
    TicketCommentType,
    TicketPriority,
    TicketRequiredMaterial,
    TicketStatus,
    TicketStatusTransition,
    TicketTransitionAction,
)
from crm_backend.repositories import (
    ClientRepository,
    CrmRoleRepository,
    CrmUserRepository,
    LocationRepository,
    TicketRepository,
)
from crm_backend.schemas.tickets import CreateTicketRequest
from crm_backend.services.activity_log_service import ActivityLogService
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.notification_service import NotificationService
from crm_backend.services.permission_service import PERMISSION_TICKET_REASSIGN, PermissionService
from crm_backend.models.notification import NotificationEntityType, NotificationType


_logger = logging.getLogger(__name__)


class TicketApplicationService:
    """Orchestrate ticket lifecycle, comments, assignment, and attachments."""

    ROLE_KEY_ALIASES = {
        "admin": "admin_crm",
        "deposito": "encargado_deposito",
        "tecnico": "tecnico_campo",
    }

    OPERATIONAL_ROLE_KEYS = {"admin", "ejecutivo", "tecnico", "deposito"}

    ALLOWED_STATUS_TRANSITIONS = {
        TicketStatus.OPEN.value: {TicketStatus.IN_PROGRESS.value, TicketStatus.ON_HOLD.value, TicketStatus.RESOLVED.value},
        TicketStatus.IN_PROGRESS.value: {TicketStatus.OPEN.value, TicketStatus.ON_HOLD.value, TicketStatus.RESOLVED.value},
        TicketStatus.ON_HOLD.value: {TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.RESOLVED.value},
        TicketStatus.RESOLVED.value: {TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.ON_HOLD.value},
        TicketStatus.PENDING_APPROVAL.value: {TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.ON_HOLD.value, TicketStatus.RESOLVED.value},
        TicketStatus.CLOSED.value: set(),
    }

    def __init__(
        self,
        ticket_repository: TicketRepository,
        client_repository: ClientRepository,
        location_repository: LocationRepository,
        user_repository: CrmUserRepository,
        role_repository: CrmRoleRepository,
        media_storage: TaskMediaStorageFacade,
        notification_service: NotificationService | None = None,
        permission_service: PermissionService | None = None,
        activity_log_service: ActivityLogService | None = None,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._client_repository = client_repository
        self._location_repository = location_repository
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._media_storage = media_storage
        self._notification_service = notification_service
        self._permission_service = permission_service
        self._activity_log_service = activity_log_service
        self._legacy_status_id_cache: dict[str, str | None] = {}
        self._legacy_priority_id_cache: dict[str, str | None] = {}

    def create_ticket(self, actor: ResolvedCrmSession, payload: CreateTicketRequest) -> Ticket:
        client = self._client_repository.get_active_by_id(payload.client_id)
        if client is None:
            raise TicketValidationError("El cliente indicado no existe o está inactivo.")

        resolved_location_id = payload.location_id
        if resolved_location_id is None:
            primary_location = self._client_repository.get_primary_location(payload.client_id)
            if primary_location is not None:
                resolved_location_id = primary_location.location_id
        if resolved_location_id is None:
            raise TicketValidationError("El ticket requiere una ubicación válida asociada al cliente.")

        location = self._location_repository.get_by_id(resolved_location_id)
        if location is None:
            raise TicketValidationError("La ubicación indicada no existe.")

        role, user = self._resolve_assignment_target(payload.assigned_role_id, payload.assigned_user_id)

        ticket = Ticket(
            ticket_number=self._next_ticket_number(),
            title=payload.title.strip(),
            description=payload.description.strip(),
            client_id=payload.client_id,
            location_id=resolved_location_id,
            status=TicketStatus.IN_PROGRESS.value if user is not None else TicketStatus.OPEN.value,
            priority=payload.priority,
            requires_arrival_comment=bool(payload.requires_arrival_comment),
            requires_video_evidence=bool(payload.requires_video_evidence),
            assigned_role_id=role.crm_role_id if role is not None else None,
            assigned_user_id=user.crm_user_id if user is not None else None,
            created_by_crm_user_id=actor.crm_user.crm_user_id,
        )
        self._sync_legacy_ticket_fields(ticket)
        if role is not None or user is not None:
            ticket.assignment_history.append(
                TicketAssignmentHistory(
                    assigned_role_id=role.crm_role_id if role is not None else None,
                    assigned_user_id=user.crm_user_id if user is not None else None,
                    assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                    notes="Asignación inicial del ticket.",
                )
            )

        self._append_required_materials(ticket, payload)

        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.created",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "ticket_number": ticket.ticket_number,
                    "client_id": ticket.client_id,
                    "location_id": ticket.location_id,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "assigned_role_id": ticket.assigned_role_id,
                    "assigned_user_id": ticket.assigned_user_id,
                },
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event("ticket.created", actor, saved_ticket, {"status": saved_ticket.status})
        self._notify_ticket_unassigned_to_tecnicos(saved_ticket)
        return saved_ticket

    def list_tickets_assigned_to_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
        self._ensure_read_access(actor)
        try:
            return self._ticket_repository.list_tickets_assigned_to_user(actor.crm_user.crm_user_id)
        except Exception:
            _logger.exception("Failed to list assigned tickets for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_unassigned_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
        self._ensure_read_access(actor)
        role_ids = sorted(self._actor_role_ids(actor))
        try:
            return self._ticket_repository.list_unassigned_tickets_for_roles(role_ids)
        except Exception:
            _logger.exception("Failed to list unassigned tickets for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_tracking_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
        self._ensure_read_access(actor)
        actor_role_keys = self._normalized_actor_role_keys(actor)
        try:
            if {"admin", "ejecutivo"}.intersection(actor_role_keys):
                return self._ticket_repository.list_tracking_tickets_for_all_roles()
            role_ids = sorted(self._actor_role_ids(actor))
            return self._ticket_repository.list_tracking_tickets_for_roles(role_ids)
        except Exception:
            _logger.exception("Failed to list tracking tickets for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def list_closed_tickets_for_actor(self, actor: ResolvedCrmSession) -> list[Ticket]:
        self._ensure_read_access(actor)
        try:
            if {"admin", "ejecutivo"}.intersection(self._normalized_actor_role_keys(actor)):
                return self._ticket_repository.list_closed_tickets()
            return self._ticket_repository.list_closed_tickets_for_user(actor.crm_user.crm_user_id)
        except Exception:
            _logger.exception("Failed to list closed tickets for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def get_ticket_detail(self, actor: ResolvedCrmSession, ticket_id: str) -> Ticket:
        self._ensure_read_access(actor)
        ticket = self._ticket_repository.get_ticket_detail(ticket_id)
        if ticket is None:
            raise TicketNotFoundError()
        if self._can_view_ticket(actor, ticket):
            return ticket
        raise TicketAccessDeniedError("El usuario no puede consultar este ticket.")

    def list_assignable_roles(self, actor: ResolvedCrmSession) -> list[CrmRole]:
        self._ensure_read_access(actor)
        actor_role_keys = self._normalized_actor_role_keys(actor)
        try:
            roles = [role for role in self._role_repository.list_active() if self._is_operational_role(role.role_key)]
            if {"admin", "ejecutivo"}.intersection(actor_role_keys):
                return roles

            actor_role_ids = self._actor_role_ids(actor)
            if {"tecnico", "deposito"}.intersection(actor_role_keys):
                for role in roles:
                    normalized = self._normalize_role_key(role.role_key)
                    if normalized in {"admin", "tecnico", "deposito"}:
                        actor_role_ids.add(role.crm_role_id)
            return [role for role in roles if role.crm_role_id in actor_role_ids]
        except Exception:
            _logger.exception("Failed to list assignable roles for actor %s", getattr(actor.crm_user, "crm_user_id", "unknown"))
            return []

    def add_comment(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        body: str,
        location_id: str | None,
        attachment_ids: list[str],
        mentioned_user_ids: list[str] | None = None,
        comment_type: str = TicketCommentType.GENERAL.value,
    ) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        self._ensure_ticket_operable(actor, ticket)
        normalized_body = body.strip()
        if not normalized_body:
            raise TicketValidationError("El comentario no puede estar vacío.")

        resolved_location_id: str | None = None
        if location_id:
            location = self._location_repository.get_by_id(location_id)
            if location is None:
                raise TicketValidationError("La ubicación indicada para el comentario no existe.")
            resolved_location_id = location.location_id

        comment = TicketComment(
            ticket_comment_id=str(uuid4()),
            ticket_id=ticket.ticket_id,
            author_crm_user_id=actor.crm_user.crm_user_id,
            location_id=resolved_location_id,
            comment_type=comment_type,
            body=normalized_body,
        )
        ticket.comments.append(comment)
        self._attach_files_to_comment(ticket, comment, attachment_ids)
        mentioned_users = self._resolve_mentioned_users(mentioned_user_ids or [])
        for mentioned_user in mentioned_users:
            comment.mentions.append(
                TicketCommentMention(
                    mentioned_crm_user_id=mentioned_user.crm_user_id,
                    created_by_crm_user_id=actor.crm_user.crm_user_id,
                )
            )
        self._try_register_arrival_from_comment(
            actor=actor,
            ticket=ticket,
            comment=comment,
            has_multimedia=bool(attachment_ids),
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.comment_added",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "comment_type": comment_type,
                    "ticket_comment_id": comment.ticket_comment_id,
                    "location_id": resolved_location_id,
                },
            )
        )
        for mentioned_user in mentioned_users:
            self._log_comment_mention(actor, ticket, comment, mentioned_user)
        saved_ticket = self._ticket_repository.save(ticket)

        try:
            if self._notification_service is not None:
                recipient_ids = self._resolve_notification_recipients_for_event(
                    event_code=NotificationType.TICKET_COMMENT_ADDED.value,
                    assigned_user_id=saved_ticket.assigned_user_id,
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                )
                actor_name = actor.crm_user.display_name or actor.crm_user.email or actor.crm_user.crm_user_id
                for recipient_id in recipient_ids:
                    self._notification_service.notify(
                        recipient_crm_user_id=recipient_id,
                        notification_type=NotificationType.TICKET_COMMENT_ADDED,
                        title=f"Nuevo comentario en ticket {saved_ticket.ticket_number}",
                        body=f"{actor_name} agregó un comentario en {saved_ticket.ticket_number}.",
                        entity_type=NotificationEntityType.TICKET,
                        entity_id=saved_ticket.ticket_id,
                    )
                for mentioned_user in mentioned_users:
                    self._notification_service.notify(
                        recipient_crm_user_id=mentioned_user.crm_user_id,
                        notification_type=NotificationType.TICKET_COMMENT_MENTIONED,
                        title=f"Te mencionaron en ticket {saved_ticket.ticket_number}",
                        body=f"{actor_name} te mencionó en un comentario de {saved_ticket.ticket_number}.",
                        entity_type=NotificationEntityType.TICKET,
                        entity_id=saved_ticket.ticket_id,
                        metadata={
                            "comment_id": comment.ticket_comment_id,
                            "mentioned_by_crm_user_id": actor.crm_user.crm_user_id,
                        },
                    )
        except Exception:
            _logger.exception("Error sending add_comment notification for ticket %s", saved_ticket.ticket_id)

        return saved_ticket

    def assign_ticket(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        assigned_role_id: str | None,
        assigned_user_id: str | None,
        notes: str | None,
    ) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        role, user = self._resolve_assignment_target(assigned_role_id, assigned_user_id)
        self._ensure_assignment_access(actor, ticket, role)

        if ticket.assigned_role_id == (role.crm_role_id if role is not None else None) and ticket.assigned_user_id == (
            user.crm_user_id if user is not None else None
        ):
            raise TicketValidationError("El ticket ya tiene la asignación indicada.")

        previous_role_id = ticket.assigned_role_id
        previous_user_id = ticket.assigned_user_id

        ticket.assigned_role_id = role.crm_role_id if role is not None else None
        ticket.assigned_user_id = user.crm_user_id if user is not None else None
        if ticket.status == TicketStatus.OPEN.value and user is not None:
            ticket.status = TicketStatus.IN_PROGRESS.value
        self._sync_legacy_ticket_fields(ticket)

        ticket.assignment_history.append(
            TicketAssignmentHistory(
                previous_role_id=previous_role_id,
                previous_user_id=previous_user_id,
                assigned_role_id=ticket.assigned_role_id,
                assigned_user_id=ticket.assigned_user_id,
                assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                notes=(notes or "").strip() or None,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.assignment_changed",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "previous_role_id": previous_role_id,
                    "previous_user_id": previous_user_id,
                    "assigned_role_id": ticket.assigned_role_id,
                    "assigned_user_id": ticket.assigned_user_id,
                },
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event(
            "ticket.reassigned",
            actor,
            saved_ticket,
            {"assigned_role_id": saved_ticket.assigned_role_id, "assigned_user_id": saved_ticket.assigned_user_id},
        )
        # Notify the newly assigned user when there is one.
        try:
            if self._notification_service is not None and saved_ticket.assigned_user_id is not None:
                is_reassignment = previous_user_id is not None and previous_user_id != saved_ticket.assigned_user_id
                notif_type = NotificationType.TICKET_REASSIGNED if is_reassignment else NotificationType.TICKET_ASSIGNED
                self._notification_service.notify(
                    recipient_crm_user_id=saved_ticket.assigned_user_id,
                    notification_type=notif_type,
                    title=f"Ticket {saved_ticket.ticket_number} asignado a vos",
                    body=f"Se te asignó el ticket {saved_ticket.ticket_number}: {saved_ticket.title}",
                    entity_type=NotificationEntityType.TICKET,
                    entity_id=saved_ticket.ticket_id,
                )
            elif self._notification_service is not None and saved_ticket.assigned_user_id is None:
                self._notify_ticket_unassigned_to_tecnicos(saved_ticket)
        except Exception:
            _logger.exception("Error sending assign_ticket notification for ticket %s", saved_ticket.ticket_id)
        return saved_ticket

    def update_status(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        to_status: str,
        comment: str | None,
        attachment_ids: list[str],
    ) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        self._ensure_ticket_operable(actor, ticket)
        self._ensure_no_pending_receipt_for_actor(actor, ticket)
        self._ensure_valid_transition(ticket.status, to_status)

        from_status = ticket.status
        ticket_comment = None
        normalized_comment = (comment or "").strip()
        if normalized_comment:
            ticket_comment = TicketComment(
                ticket_comment_id=str(uuid4()),
                ticket_id=ticket.ticket_id,
                author_crm_user_id=actor.crm_user.crm_user_id,
                comment_type=TicketCommentType.SYSTEM.value,
                body=normalized_comment,
            )
            ticket.comments.append(ticket_comment)
            self._attach_files_to_comment(ticket, ticket_comment, attachment_ids)
        elif attachment_ids:
            raise TicketValidationError("No se pueden asociar adjuntos sin comentario de transición.")

        ticket.status = to_status
        if to_status == TicketStatus.RESOLVED.value:
            ticket.resolved_at = datetime.now(UTC)
            ticket.resolved_by_crm_user_id = actor.crm_user.crm_user_id
        elif from_status in {TicketStatus.RESOLVED.value, TicketStatus.PENDING_APPROVAL.value} and to_status != TicketStatus.RESOLVED.value:
            ticket.resolved_at = None
            ticket.resolved_by_crm_user_id = None

        if from_status == TicketStatus.PENDING_APPROVAL.value:
            ticket.closed_at = None
            ticket.closed_by_crm_user_id = None
        self._sync_legacy_ticket_fields(ticket)

        ticket.status_history.append(
            TicketStatusTransition(
                ticket_id=ticket.ticket_id,
                from_status=from_status,
                to_status=to_status,
                action=self._transition_action_for_status(to_status),
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
                ticket_comment_id=ticket_comment.ticket_comment_id if ticket_comment is not None else None,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.status_changed",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={"from_status": from_status, "to_status": to_status},
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event(
            "ticket.status_changed",
            actor,
            saved_ticket,
            {"from_status": from_status, "to_status": to_status},
        )
        return saved_ticket

    def register_arrival(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        body: str,
        attachment_ids: list[str],
    ) -> Ticket:
        """Backward-compatible endpoint: create a comment that can auto-register arrival."""
        ticket = self.get_ticket_detail(actor, ticket_id)
        if ticket.status == TicketStatus.CLOSED.value:
            raise TicketConflictError("No se puede registrar llegada en un ticket cerrado.")
        if not attachment_ids:
            raise TicketValidationError("El registro de llegada requiere al menos un adjunto multimedia.")

        return self.add_comment(
            actor=actor,
            ticket_id=ticket_id,
            body=body,
            location_id=ticket.location_id,
            attachment_ids=attachment_ids,
            comment_type=TicketCommentType.GENERAL.value,
        )

    def has_arrival_registered(self, ticket: Ticket) -> bool:
        """Expose arrival registration status for API serialization."""
        return self._has_arrival_registered(ticket)

    def can_register_arrival(self, actor: ResolvedCrmSession, ticket: Ticket) -> bool:
        """Return whether the current actor can register arrival for this ticket."""
        if not ticket.requires_arrival_comment:
            return False
        if ticket.status == TicketStatus.CLOSED.value:
            return False
        if self._has_arrival_registered(ticket):
            return False
        if "deposito" in actor.role_keys:
            return False
        try:
            self._ensure_ticket_operable(actor, ticket)
        except TicketAccessDeniedError:
            return False
        return True

    def close_ticket(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        comment: str,
        attachment_ids: list[str],
        *,
        via_solution_comment: bool = False,
        solution_comment_id: str | None = None,
    ) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        self._ensure_ticket_operable(actor, ticket)
        self._ensure_no_pending_receipt_for_actor(actor, ticket)
        if ticket.status == TicketStatus.CLOSED.value:
            raise TicketConflictError("El ticket ya se encuentra cerrado.")

        if ticket.requires_arrival_comment and ticket.arrival_registered_at is None:
            raise TicketConflictError(
                "Este ticket requiere registrar llegada antes de poder cerrarse.\n"
                "Agregá un comentario con multimedia y ubicación asociada."
            )

        from_status = ticket.status
        ticket_comment_id: str | None = None
        if via_solution_comment:
            if not solution_comment_id:
                raise TicketValidationError("Debes indicar un comentario para marcar como solución.")

            solution_comment = next((item for item in ticket.comments if item.ticket_comment_id == solution_comment_id), None)
            if solution_comment is None:
                raise TicketValidationError("El comentario indicado no existe en este ticket.")
            if solution_comment.comment_type != TicketCommentType.GENERAL.value:
                raise TicketValidationError("Solo se pueden marcar como solución comentarios de tipo general.")

            ticket.solution_comment_id = solution_comment.ticket_comment_id
            ticket_comment_id = solution_comment.ticket_comment_id
        else:
            ticket.solution_comment_id = None
            normalized_comment = comment.strip()
            if not normalized_comment:
                raise TicketValidationError("No se puede cerrar un ticket sin comentario de cierre.")

            ticket_comment = TicketComment(
                ticket_comment_id=str(uuid4()),
                ticket_id=ticket.ticket_id,
                author_crm_user_id=actor.crm_user.crm_user_id,
                comment_type=TicketCommentType.CLOSURE_EVIDENCE.value,
                body=normalized_comment,
            )
            ticket.comments.append(ticket_comment)
            self._attach_files_to_comment(ticket, ticket_comment, attachment_ids)
            ticket_comment_id = ticket_comment.ticket_comment_id

            if ticket.requires_video_evidence and not self._comment_has_video(ticket, ticket_comment):
                raise TicketValidationError(
                    "El cierre del ticket requiere al menos un video de evidencia adjunto."
                )

        is_executive_closure = bool({"admin", "ejecutivo"}.intersection(actor.role_keys))
        if is_executive_closure:
            ticket.status = TicketStatus.CLOSED.value
            ticket.closed_at = datetime.now(UTC)
            ticket.closed_by_crm_user_id = actor.crm_user.crm_user_id
            if ticket.resolved_at is None:
                ticket.resolved_at = ticket.closed_at
                ticket.resolved_by_crm_user_id = actor.crm_user.crm_user_id
        else:
            executive_role = self._role_repository.get_by_key("ejecutivo")
            if executive_role is None:
                raise TicketValidationError("No existe un rol ejecutivo activo para aprobar el cierre del ticket.")
            ticket.status = TicketStatus.PENDING_APPROVAL.value
            ticket.assigned_role_id = executive_role.crm_role_id
            ticket.assigned_user_id = None
            ticket.closed_at = None
            ticket.closed_by_crm_user_id = None
            if ticket.resolved_at is None:
                ticket.resolved_at = datetime.now(UTC)
                ticket.resolved_by_crm_user_id = actor.crm_user.crm_user_id
        self._sync_legacy_ticket_fields(ticket)

        ticket.status_history.append(
            TicketStatusTransition(
                ticket_id=ticket.ticket_id,
                from_status=from_status,
                to_status=ticket.status,
                action=TicketTransitionAction.CLOSE.value if is_executive_closure else TicketTransitionAction.SUBMIT_FOR_APPROVAL.value,
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
                ticket_comment_id=ticket_comment_id,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.closed" if is_executive_closure else "ticket.pending_executive_approval",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "from_status": from_status,
                    "closed_by": actor.crm_user.crm_user_id,
                    "to_status": ticket.status,
                    "via_solution_comment": via_solution_comment,
                    "solution_comment_id": ticket.solution_comment_id,
                },
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event("ticket.closed", actor, saved_ticket, {"status": saved_ticket.status})
        # If sent to approval, notify all executives/admins.
        try:
            if self._notification_service is not None and not is_executive_closure:
                exec_user_ids = self._notification_service.resolve_users_with_role_key("ejecutivo")
                admin_user_ids = self._notification_service.resolve_users_with_role_key("admin_crm")
                recipients = list({*exec_user_ids, *admin_user_ids} - {actor.crm_user.crm_user_id})
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=recipients,
                    notification_type=NotificationType.TICKET_PENDING_APPROVAL,
                    title=f"Ticket {saved_ticket.ticket_number} pendiente de aprobación",
                    body=f"El ticket {saved_ticket.ticket_number}: {saved_ticket.title} está esperando aprobación ejecutiva.",
                    entity_type=NotificationEntityType.TICKET,
                    entity_id=saved_ticket.ticket_id,
                )
        except Exception:
            _logger.exception("Error sending close_ticket notification for ticket %s", saved_ticket.ticket_id)
        return saved_ticket

    def mark_comment_as_solution(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        comment_id: str,
    ) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        self._ensure_ticket_operable(actor, ticket)
        self._ensure_no_pending_receipt_for_actor(actor, ticket)

        comment = next((item for item in ticket.comments if item.ticket_comment_id == comment_id), None)
        if comment is None:
            raise TicketValidationError("El comentario indicado no existe en este ticket.")
        if comment.comment_type != TicketCommentType.GENERAL.value:
            raise TicketValidationError("Solo los comentarios generales pueden marcarse como solución.")

        return self.close_ticket(
            actor,
            ticket_id,
            comment=comment.body,
            attachment_ids=[],
            via_solution_comment=True,
            solution_comment_id=comment.ticket_comment_id,
        )

    def approve_ticket(self, actor: ResolvedCrmSession, ticket_id: str, comment: str | None) -> Ticket:
        self._ensure_admin_or_executive(actor)
        ticket = self.get_ticket_detail(actor, ticket_id)
        if ticket.status != TicketStatus.PENDING_APPROVAL.value:
            raise TicketConflictError("El ticket no está pendiente de aprobación ejecutiva.")

        from_status = ticket.status
        normalized_comment = (comment or "").strip()
        ticket_comment: TicketComment | None = None
        if normalized_comment:
            ticket_comment = TicketComment(
                ticket_comment_id=str(uuid4()),
                ticket_id=ticket.ticket_id,
                author_crm_user_id=actor.crm_user.crm_user_id,
                comment_type=TicketCommentType.CLOSURE.value,
                body=normalized_comment,
            )
            ticket.comments.append(ticket_comment)
            self._ticket_repository.session.flush()

        ticket.status = TicketStatus.CLOSED.value
        ticket.closed_at = datetime.now(UTC)
        ticket.closed_by_crm_user_id = actor.crm_user.crm_user_id
        ticket.assigned_user_id = None
        ticket.assigned_role_id = None
        if ticket.resolved_at is None:
            ticket.resolved_at = ticket.closed_at
            ticket.resolved_by_crm_user_id = actor.crm_user.crm_user_id
        self._sync_legacy_ticket_fields(ticket)

        ticket.status_history.append(
            TicketStatusTransition(
                ticket_id=ticket.ticket_id,
                from_status=from_status,
                to_status=TicketStatus.CLOSED.value,
                action=TicketTransitionAction.APPROVE_CLOSE.value,
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
                ticket_comment_id=ticket_comment.ticket_comment_id if ticket_comment is not None else None,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.approved_by_executive",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={"from_status": from_status, "ticket_id": ticket.ticket_id},
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event("ticket.approved", actor, saved_ticket, {"status": saved_ticket.status})
        # Notify the technician who originally resolved the ticket.
        try:
            if self._notification_service is not None and saved_ticket.resolved_by_crm_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=saved_ticket.resolved_by_crm_user_id,
                    notification_type=NotificationType.TICKET_APPROVED,
                    title=f"Ticket {saved_ticket.ticket_number} aprobado",
                    body=f"El ticket {saved_ticket.ticket_number}: {saved_ticket.title} fue aprobado y cerrado por un ejecutivo.",
                    entity_type=NotificationEntityType.TICKET,
                    entity_id=saved_ticket.ticket_id,
                )
        except Exception:
            _logger.exception("Error sending approve_ticket notification for ticket %s", saved_ticket.ticket_id)
        return saved_ticket

    def reject_ticket_approval(self, actor: ResolvedCrmSession, ticket_id: str, comment: str) -> Ticket:
        self._ensure_admin_or_executive(actor)
        ticket = self.get_ticket_detail(actor, ticket_id)
        if ticket.status != TicketStatus.PENDING_APPROVAL.value:
            raise TicketConflictError("El ticket no está pendiente de aprobación ejecutiva.")

        normalized_comment = comment.strip()
        if not normalized_comment:
            raise TicketValidationError("El rechazo del cierre requiere un comentario obligatorio.")

        from_status = ticket.status
        next_role_id, next_user_id = self._resolve_reopen_assignment(ticket)
        reject_comment = TicketComment(
            ticket_comment_id=str(uuid4()),
            ticket_id=ticket.ticket_id,
            author_crm_user_id=actor.crm_user.crm_user_id,
            comment_type=TicketCommentType.CLOSURE.value,
            body=normalized_comment,
        )
        ticket.comments.append(reject_comment)
        self._ticket_repository.session.flush()

        ticket.status = TicketStatus.IN_PROGRESS.value
        ticket.closed_at = None
        ticket.closed_by_crm_user_id = None
        ticket.resolved_at = None
        ticket.resolved_by_crm_user_id = None
        ticket.assigned_role_id = next_role_id
        ticket.assigned_user_id = next_user_id
        self._sync_legacy_ticket_fields(ticket)

        ticket.status_history.append(
            TicketStatusTransition(
                ticket_id=ticket.ticket_id,
                from_status=from_status,
                to_status=TicketStatus.IN_PROGRESS.value,
                action=TicketTransitionAction.REJECT_CLOSE.value,
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
                ticket_comment_id=reject_comment.ticket_comment_id,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.rejected_by_executive",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "from_status": from_status,
                    "ticket_id": ticket.ticket_id,
                    "assigned_user_id": next_user_id,
                    "assigned_role_id": next_role_id,
                },
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        self._log_event("ticket.reopened", actor, saved_ticket, {"status": saved_ticket.status})
        try:
            if self._notification_service is not None and next_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=next_user_id,
                    notification_type=NotificationType.TICKET_REJECTED,
                    title=f"Ticket {saved_ticket.ticket_number} rechazado por ejecutivo",
                    body=f"El cierre del ticket {saved_ticket.ticket_number}: {saved_ticket.title} fue rechazado. Revisá el comentario y retomá el trabajo.",
                    entity_type=NotificationEntityType.TICKET,
                    entity_id=saved_ticket.ticket_id,
                )
        except Exception:
            _logger.exception("Error sending reject_ticket_approval notification for ticket %s", saved_ticket.ticket_id)
        return saved_ticket

    def reopen_ticket(self, actor: ResolvedCrmSession, ticket_id: str, comment: str) -> Ticket:
        ticket = self.get_ticket_detail(actor, ticket_id)
        if ticket.status != TicketStatus.CLOSED.value:
            raise TicketConflictError("Solo se puede reabrir un ticket cerrado.")
        if not self._can_reopen_ticket(actor, ticket):
            raise TicketAccessDeniedError("Solo administrador, ejecutivo o quien cerró el ticket puede reabrirlo.")

        normalized_comment = comment.strip()
        if not normalized_comment:
            raise TicketValidationError("No se puede reabrir un ticket sin comentario obligatorio.")

        from_status = ticket.status
        previous_role_id = ticket.assigned_role_id
        previous_user_id = ticket.assigned_user_id
        next_role_id, next_user_id = self._resolve_reopen_assignment(ticket)

        reopen_comment = TicketComment(
            ticket_comment_id=str(uuid4()),
            ticket_id=ticket.ticket_id,
            author_crm_user_id=actor.crm_user.crm_user_id,
            comment_type=TicketCommentType.SYSTEM.value,
            body=normalized_comment,
        )
        ticket.comments.append(reopen_comment)

        ticket.status = TicketStatus.IN_PROGRESS.value
        ticket.assigned_role_id = next_role_id
        ticket.assigned_user_id = next_user_id
        ticket.closed_at = None
        ticket.closed_by_crm_user_id = None
        ticket.resolved_at = None
        ticket.resolved_by_crm_user_id = None
        self._sync_legacy_ticket_fields(ticket)

        if previous_role_id != next_role_id or previous_user_id != next_user_id:
            ticket.assignment_history.append(
                TicketAssignmentHistory(
                    previous_role_id=previous_role_id,
                    previous_user_id=previous_user_id,
                    assigned_role_id=next_role_id,
                    assigned_user_id=next_user_id,
                    assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                    notes="Reasignación automática por reapertura de ticket.",
                )
            )

        ticket.status_history.append(
            TicketStatusTransition(
                ticket_id=ticket.ticket_id,
                from_status=from_status,
                to_status=TicketStatus.IN_PROGRESS.value,
                action=TicketTransitionAction.REOPEN.value,
                performed_by_crm_user_id=actor.crm_user.crm_user_id,
                ticket_comment_id=reopen_comment.ticket_comment_id,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.reopened",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "from_status": from_status,
                    "to_status": TicketStatus.IN_PROGRESS.value,
                    "ticket_comment_id": reopen_comment.ticket_comment_id,
                    "assigned_role_id": next_role_id,
                    "assigned_user_id": next_user_id,
                },
            )
        )
        saved_ticket = self._ticket_repository.save(ticket)
        # Notify the user to whom the ticket was reassigned after reopen.
        try:
            if self._notification_service is not None and saved_ticket.assigned_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=saved_ticket.assigned_user_id,
                    notification_type=NotificationType.TICKET_REOPENED,
                    title=f"Ticket {saved_ticket.ticket_number} reabierto",
                    body=f"El ticket {saved_ticket.ticket_number}: {saved_ticket.title} fue reabierto y está asignado a vos.",
                    entity_type=NotificationEntityType.TICKET,
                    entity_id=saved_ticket.ticket_id,
                )
        except Exception:
            _logger.exception("Error sending reopen_ticket notification for ticket %s", saved_ticket.ticket_id)
        return saved_ticket

    def _has_arrival_registered(self, ticket: Ticket) -> bool:
        """Return True when arrival metadata is already persisted in the ticket."""
        if ticket.arrival_registered_at is not None:
            return True
        if ticket.arrival_comment_id is not None:
            return True
        return any(comment.comment_type == TicketCommentType.ARRIVAL_REGISTRATION.value for comment in ticket.comments)

    def _comment_has_location(self, comment: TicketComment) -> bool:
        """Return True when the comment is linked to a location with coordinates."""
        return bool(comment.location_id)

    def _try_register_arrival_from_comment(
        self,
        *,
        actor: ResolvedCrmSession,
        ticket: Ticket,
        comment: TicketComment,
        has_multimedia: bool,
    ) -> None:
        """Persist arrival only once using a conditional DB update to avoid race conditions."""
        if not has_multimedia:
            return
        if not self._comment_has_location(comment):
            return
        if not ticket.requires_arrival_comment:
            return
        if ticket.arrival_registered_at is not None or ticket.arrival_comment_id is not None:
            return

        registered_at = datetime.now(UTC)
        self._ticket_repository.session.flush()
        if self._ticket_repository.session.get_bind().dialect.name != "postgresql":
            if ticket.arrival_registered_at is None and ticket.arrival_comment_id is None:
                ticket.arrival_registered_at = registered_at
                ticket.arrival_comment_id = comment.ticket_comment_id
                ticket.audit_events.append(
                    TicketAuditEvent(
                        event_type="ticket.arrival_registered",
                        actor_crm_user_id=actor.crm_user.crm_user_id,
                        payload_json={
                            "ticket_comment_id": comment.ticket_comment_id,
                            "location_id": comment.location_id,
                            "attachment_ids": [
                                attachment.attachment_id
                                for attachment in ticket.attachments
                                if attachment.ticket_comment_id == comment.ticket_comment_id
                            ],
                        },
                    )
                )
            return

        self._ticket_repository.session.execute(
            text(
                "UPDATE tickets "
                "SET arrival_registered_at = :registered_at, "
                "    arrival_comment_id = :comment_id "
                "WHERE ticket_id = :ticket_id "
                "  AND arrival_registered_at IS NULL "
                "  AND arrival_comment_id IS NULL"
            ),
            {
                "registered_at": registered_at,
                "comment_id": comment.ticket_comment_id,
                "ticket_id": ticket.ticket_id,
            },
        )
        persisted = self._ticket_repository.session.execute(
            text(
                "SELECT arrival_registered_at, arrival_comment_id "
                "FROM tickets "
                "WHERE ticket_id = :ticket_id"
            ),
            {"ticket_id": ticket.ticket_id},
        ).first()
        if persisted is not None:
            ticket.arrival_registered_at = persisted[0]
            ticket.arrival_comment_id = persisted[1]
            if ticket.arrival_comment_id == comment.ticket_comment_id:
                ticket.audit_events.append(
                    TicketAuditEvent(
                        event_type="ticket.arrival_registered",
                        actor_crm_user_id=actor.crm_user.crm_user_id,
                        payload_json={
                            "ticket_comment_id": comment.ticket_comment_id,
                            "location_id": comment.location_id,
                            "attachment_ids": [
                                attachment.attachment_id
                                for attachment in ticket.attachments
                                if attachment.ticket_comment_id == comment.ticket_comment_id
                            ],
                        },
                    )
                )

    def _comment_has_video(self, ticket: Ticket, comment: TicketComment) -> bool:
        """Return True if at least one attachment linked to `comment` is a video."""
        from crm_backend.models import TicketAttachmentType
        return any(
            attachment.attachment_type == TicketAttachmentType.VIDEO.value
            for attachment in ticket.attachments
            if attachment.ticket_comment_id == comment.ticket_comment_id
        )

    def _ensure_no_pending_receipt_for_actor(self, actor: ResolvedCrmSession, ticket: Ticket) -> None:
        result = self._ticket_repository.session.execute(
            text(
                """
                SELECT 1
                FROM inventory_requests
                WHERE external_ticket_id = :ticket_id
                  AND request_status = 'PENDING_RECEIPT'
                LIMIT 1
                """
            ),
            {"ticket_id": ticket.ticket_id},
        ).scalar_one_or_none()
        if result is not None:
            raise TicketConflictError(
                "Debes confirmar la recepción del despacho pendiente antes de cambiar el estado o cerrar el ticket."
            )

    async def upload_ticket_attachments(
        self,
        actor: ResolvedCrmSession,
        ticket_id: str,
        files: list[UploadFile],
    ) -> list[TicketAttachment]:
        if not files:
            raise InvalidTaskAttachmentError("Se requiere al menos un archivo para subir multimedia.")

        ticket = self.get_ticket_detail(actor, ticket_id)

        stored_media_batch: list[StoredTaskMedia] = []
        persisted_attachments: list[TicketAttachment] = []
        try:
            for upload in files:
                stored_media = await self._media_storage.store(upload)
                stored_media_batch.append(stored_media)
                attachment = TicketAttachment(
                    ticket_id=ticket.ticket_id,
                    file_name=stored_media.file_name,
                    file_url=stored_media.file_url,
                    file_size_bytes=stored_media.file_size_bytes,
                    mime_type=stored_media.mime_type,
                    attachment_type=stored_media.attachment_type,
                    uploaded_by_crm_user_id=actor.crm_user.crm_user_id,
                )
                self._ticket_repository.session.add(attachment)
                persisted_attachments.append(attachment)
            self._ticket_repository.session.commit()
        except Exception:
            self._ticket_repository.session.rollback()
            for stored_media in stored_media_batch:
                self._media_storage.delete(stored_media)
            raise

        for attachment in persisted_attachments:
            self._ticket_repository.session.refresh(attachment)
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.attachment_uploaded",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={"attachment_ids": [item.attachment_id for item in persisted_attachments]},
            )
        )
        self._ticket_repository.save(ticket)
        return persisted_attachments

    def delete_ticket_attachment(self, actor: ResolvedCrmSession, attachment_id: str) -> None:
        attachment = self._ticket_repository.get_attachment(attachment_id)
        if attachment is None:
            raise TaskAttachmentNotFoundError()
        if attachment.uploaded_by_crm_user_id != actor.crm_user.crm_user_id and "admin" not in actor.role_keys:
            raise TicketAccessDeniedError("No podés eliminar adjuntos subidos por otro usuario.")
        if attachment.ticket_comment_id is not None:
            raise TicketConflictError("El adjunto ya quedó asociado a un comentario persistido y no puede eliminarse.")

        self._media_storage.delete_from_persisted_values(
            attachment_type=attachment.attachment_type,
            file_name=attachment.file_name,
            file_url=attachment.file_url,
            mime_type=attachment.mime_type,
            file_size_bytes=attachment.file_size_bytes,
        )
        self._ticket_repository.session.delete(attachment)
        self._ticket_repository.session.commit()

    def _attach_files_to_comment(self, ticket: Ticket, comment: TicketComment, attachment_ids: list[str]) -> None:
        if not attachment_ids:
            return
        attachment_ids_set = set(attachment_ids)
        if len(attachment_ids_set) != len(attachment_ids):
            raise TicketValidationError("No se pueden repetir adjuntos dentro del mismo comentario.")

        for attachment_id in attachment_ids:
            attachment = self._ticket_repository.get_attachment(attachment_id)
            if attachment is None or attachment.ticket_id != ticket.ticket_id:
                raise TicketValidationError("Alguno de los adjuntos indicados no pertenece a este ticket.")
            if attachment.ticket_comment_id is not None:
                raise TicketValidationError("Uno de los adjuntos ya está asociado a otro comentario.")
            attachment.ticket_comment_id = comment.ticket_comment_id

    def _resolve_assignment_target(self, role_id: str | None, user_id: str | None) -> tuple[CrmRole | None, CrmUser | None]:
        role = None
        if role_id:
            role = self._role_repository.get_by_id(role_id)
            if role is None:
                raise TicketValidationError("El rol indicado no existe o está inactivo.")
            if not self._is_operational_role(role.role_key):
                raise TicketValidationError("El rol indicado no puede usarse para asignación de tickets.")

        user = None
        if user_id:
            user = self._user_repository.get_by_id(user_id)
            if user is None or user.deleted_at is not None or not user.is_active_in_crm:
                raise TicketValidationError("El usuario indicado no existe o está inactivo.")

            user_roles = [assignment.role for assignment in user.assigned_roles if assignment.role and assignment.role.is_active and self._is_operational_role(assignment.role.role_key)]
            if not user_roles:
                raise TicketValidationError("El usuario indicado no tiene roles operativos válidos para tickets.")

            if role is None:
                if len(user_roles) > 1:
                    raise TicketValidationError("Indicá también el rol para asignar un usuario con múltiples roles operativos.")
                role = user_roles[0]
            else:
                if not any(assignment.role and assignment.role.crm_role_id == role.crm_role_id for assignment in user.assigned_roles):
                    raise TicketValidationError("El usuario indicado no posee el rol seleccionado para la asignación.")

        if user is None and role is None:
            return None, None
        return role, user

    def _append_required_materials(self, ticket: Ticket, payload: CreateTicketRequest) -> None:
        if not payload.required_materials:
            return

        product_ids = [item.product_id for item in payload.required_materials]
        if len(product_ids) != len(set(product_ids)):
            raise TicketValidationError("No se puede repetir el mismo producto en materiales requeridos.")

        products = {
            product.product_id: product
            for product in self._ticket_repository.session.scalars(
                select(StockProduct).where(
                    StockProduct.product_id.in_(product_ids),
                    StockProduct.is_active.is_(True),
                    StockProduct.deleted_at.is_(None),
                )
            ).all()
        }

        for item in payload.required_materials:
            product = products.get(item.product_id)
            if product is None:
                raise TicketValidationError("Uno de los productos indicados no existe o está inactivo.")

            ticket.required_materials.append(
                TicketRequiredMaterial(
                    product_id=product.product_id,
                    quantity=int(item.quantity),
                )
            )

    def _ensure_valid_transition(self, current_status: str, to_status: str) -> None:
        allowed_targets = self.ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
        if to_status not in allowed_targets:
            raise TicketConflictError(f"No se puede pasar de {current_status} a {to_status}.")

    def _can_reopen_ticket(self, actor: ResolvedCrmSession, ticket: Ticket) -> bool:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return True
        if ticket.closed_by_crm_user_id and ticket.closed_by_crm_user_id == actor.crm_user.crm_user_id:
            return True
        return False

    def _resolve_reopen_assignment(self, ticket: Ticket) -> tuple[str | None, str | None]:
        # Prefer the latest technical assignee before closure.
        for assignment in reversed(ticket.assignment_history):
            if not assignment.assigned_user_id:
                continue
            role_id = assignment.assigned_role_id
            if role_id is None:
                continue
            role = self._role_repository.get_by_id(role_id)
            if role is None:
                continue
            if self._normalize_role_key(role.role_key) == "tecnico":
                return role.crm_role_id, assignment.assigned_user_id

        # Fallback to latest assigned user regardless of role.
        for assignment in reversed(ticket.assignment_history):
            if assignment.assigned_user_id:
                return assignment.assigned_role_id, assignment.assigned_user_id

        # Final fallback: keep current role if present, but reopen unassigned.
        return ticket.assigned_role_id, None

    def _transition_action_for_status(self, to_status: str) -> str:
        if to_status == TicketStatus.IN_PROGRESS.value:
            return TicketTransitionAction.START_WORK.value
        if to_status == TicketStatus.ON_HOLD.value:
            return TicketTransitionAction.PUT_ON_HOLD.value
        if to_status == TicketStatus.RESOLVED.value:
            return TicketTransitionAction.MARK_RESOLVED.value
        if to_status == TicketStatus.PENDING_APPROVAL.value:
            return TicketTransitionAction.SUBMIT_FOR_APPROVAL.value
        return TicketTransitionAction.REOPEN.value

    def _next_ticket_number(self) -> str:
        latest = self._ticket_repository.find_latest_ticket_number()
        if latest is None:
            return "TCK-000001"

        match = re.search(r"(\d+)$", latest)
        next_number = 1 if match is None else int(match.group(1)) + 1
        return f"TCK-{next_number:06d}"

    def _sync_legacy_ticket_fields(self, ticket: Ticket) -> None:
        ticket.legacy_ticket_title = ticket.title
        ticket.legacy_ticket_description = ticket.description

        legacy_status_id = self._lookup_legacy_status_id(ticket.status)
        if legacy_status_id is not None:
            ticket.legacy_status_id = legacy_status_id

        legacy_priority_id = self._lookup_legacy_priority_id(ticket.priority)
        if legacy_priority_id is not None:
            ticket.legacy_priority_id = legacy_priority_id

    def _lookup_legacy_status_id(self, status: str) -> str | None:
        normalized = (status or "").upper()
        if normalized in self._legacy_status_id_cache:
            return self._legacy_status_id_cache[normalized]

        status_key_aliases = {
            "OPEN": ["OPEN"],
            "IN_PROGRESS": ["IN_PROGRESS"],
            "ON_HOLD": ["AWAITING_APPROVAL", "ON_HOLD"],
            "RESOLVED": ["RESOLVED"],
            "CLOSED": ["CLOSED", "CANCELLED"],
        }
        fallback_keys = status_key_aliases.get(normalized, [normalized, "OPEN"])
        resolved_id = self._lookup_legacy_catalog_id("ticket_statuses", "status_id", "status_key", fallback_keys)
        self._legacy_status_id_cache[normalized] = resolved_id
        return resolved_id

    def _lookup_legacy_priority_id(self, priority: str) -> str | None:
        normalized = (priority or "").upper()
        if normalized in self._legacy_priority_id_cache:
            return self._legacy_priority_id_cache[normalized]

        priority_key_aliases = {
            "LOW": ["BAJA", "LOW"],
            "MEDIUM": ["MEDIA", "MEDIUM"],
            "HIGH": ["ALTA", "HIGH"],
            "CRITICAL": ["CRITICA", "CRITICAL"],
        }
        fallback_keys = priority_key_aliases.get(normalized, [normalized, "MEDIA"])
        resolved_id = self._lookup_legacy_catalog_id("ticket_priorities", "priority_id", "priority_key", fallback_keys)
        self._legacy_priority_id_cache[normalized] = resolved_id
        return resolved_id

    def _lookup_legacy_catalog_id(
        self,
        table_name: str,
        id_column: str,
        key_column: str,
        candidate_keys: list[str],
    ) -> str | None:
        for key in candidate_keys:
            if not key:
                continue
            try:
                result = self._ticket_repository.session.execute(
                    text(
                        f"SELECT {id_column} "
                        f"FROM {table_name} "
                        f"WHERE UPPER({key_column}) = :key "
                        "LIMIT 1"
                    ),
                    {"key": key.upper()},
                ).scalar()
            except Exception:
                return None
            if result is not None:
                return str(result)
        return None

    def _ensure_read_access(self, actor: ResolvedCrmSession) -> None:
        if not self.OPERATIONAL_ROLE_KEYS.intersection(self._normalized_actor_role_keys(actor)):
            raise TicketAccessDeniedError("El usuario no tiene permisos para operar tickets.")

    def _ensure_admin_or_executive(self, actor: ResolvedCrmSession) -> None:
        if not {"admin", "ejecutivo"}.intersection(self._normalized_actor_role_keys(actor)):
            raise TicketAccessDeniedError("La operación requiere rol administrador o ejecutivo.")

    def _normalized_actor_role_keys(self, actor: ResolvedCrmSession) -> set[str]:
        raw_role_keys = getattr(actor, "role_keys", None)
        if raw_role_keys is None:
            return set()

        normalized_role_keys: set[str] = set()
        for role_key in raw_role_keys:
            normalized_role_key = self._normalize_role_key(role_key)
            if normalized_role_key is not None:
                normalized_role_keys.add(normalized_role_key)
        return normalized_role_keys

    def _ensure_ticket_operable(self, actor: ResolvedCrmSession, ticket: Ticket) -> None:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return
        actor_user_id = actor.crm_user.crm_user_id
        actor_role_ids = self._actor_role_ids(actor)
        if ticket.assigned_user_id == actor_user_id:
            return
        if ticket.assigned_user_id is None and ticket.assigned_role_id is not None and ticket.assigned_role_id in actor_role_ids:
            return
        raise TicketAccessDeniedError("Solo el usuario asignado o el mismo rol puede operar este ticket.")

    def _ensure_assignment_access(self, actor: ResolvedCrmSession, ticket: Ticket, role: CrmRole | None) -> None:
        if self._permission_service is not None and self._permission_service.resolve(
            actor.role_keys,
            actor.crm_user.crm_user_id,
            PERMISSION_TICKET_REASSIGN,
        ):
            return
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return

        actor_role_ids = self._actor_role_ids(actor)
        roles_cache = self._role_repository.list_active()
        if not actor_role_ids:
            raise TicketAccessDeniedError("El usuario no tiene roles válidos para reasignar tickets.")

        if role is not None and role.crm_role_id not in actor_role_ids and not self._can_cross_assign_to_peer(actor, role):
            raise TicketAccessDeniedError("Solo podés asignar tickets dentro de tus propios roles.")

        if ticket.assigned_role_id is not None and ticket.assigned_role_id not in actor_role_ids:
            assigned_role = next((item for item in roles_cache if item.crm_role_id == ticket.assigned_role_id), None)
            if not self._can_cross_assign_to_peer(actor, assigned_role):
                raise TicketAccessDeniedError("Solo podés reasignar tickets dentro de tus propios roles.")

        if ticket.assigned_role_id is None and ticket.assigned_user_id != actor.crm_user.crm_user_id:
            raise TicketAccessDeniedError("No podés reasignar un ticket fuera de tu ámbito de rol.")

    def _can_escalate_to_admin(self, actor: ResolvedCrmSession, role: CrmRole) -> bool:
        return self._normalize_role_key(role.role_key) == "admin" and bool({"tecnico", "deposito"}.intersection(actor.role_keys))

    def _can_cross_assign_to_peer(self, actor: ResolvedCrmSession, role: CrmRole | None) -> bool:
        """Deposito y tecnico pueden asignarse tickets mutuamente y a admin."""
        actor_keys = self._normalized_actor_role_keys(actor)
        if not {"tecnico", "deposito"}.intersection(actor_keys):
            return False
        normalized_target = self._normalize_role_key(getattr(role, "role_key", None)) if role else None
        return normalized_target in {"admin", "tecnico", "deposito"}

    def _can_view_ticket(self, actor: ResolvedCrmSession, ticket: Ticket) -> bool:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return True

        actor_user_id = actor.crm_user.crm_user_id
        if ticket.assigned_user_id == actor_user_id:
            return True
        if ticket.created_by_crm_user_id == actor_user_id:
            return True
        if any(
            assignment.previous_user_id == actor_user_id or assignment.assigned_user_id == actor_user_id
            for assignment in ticket.assignment_history
        ):
            return True

        actor_role_ids = self._actor_role_ids(actor)
        return ticket.assigned_role_id in actor_role_ids if ticket.assigned_role_id is not None else False

    def _resolve_mentioned_users(self, mentioned_user_ids: list[str]) -> list[object]:
        normalized_ids: list[str] = []
        seen: set[str] = set()
        for raw_user_id in mentioned_user_ids:
            normalized = raw_user_id.strip() if isinstance(raw_user_id, str) else ""
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            normalized_ids.append(normalized)
        if not normalized_ids:
            return []

        users = self._user_repository.list_active_by_ids(normalized_ids)
        users_by_id = {user.crm_user_id: user for user in users}
        missing_ids = [user_id for user_id in normalized_ids if user_id not in users_by_id]
        if missing_ids:
            raise TicketValidationError("Uno de los usuarios mencionados no existe o no está activo.")
        return [users_by_id[user_id] for user_id in normalized_ids]

    def _log_comment_mention(self, actor: ResolvedCrmSession, ticket: Ticket, comment: TicketComment, mentioned_user: object) -> None:
        if self._activity_log_service is None:
            return
        actor_label = actor.crm_user.display_name or actor.crm_user.email or actor.crm_user.crm_user_id
        mentioned_label = (
            getattr(mentioned_user, "display_name", None)
            or getattr(mentioned_user, "email", None)
            or getattr(mentioned_user, "crm_user_id")
        )
        ticket_label = ticket.ticket_number or ticket.ticket_id
        self._activity_log_service.log(
            "ticket.comment_mention.created",
            actor,
            entity_type="ticket",
            entity_id=ticket.ticket_id,
            entity_label=ticket_label,
            summary=f"{actor_label} mencionó a {mentioned_label} en el ticket {ticket_label}.",
            extra={
                "comment_id": comment.ticket_comment_id,
                "mentioned_user_id": getattr(mentioned_user, "crm_user_id"),
                "mentioned_user_display_name": mentioned_label,
                "ticket_id": ticket.ticket_id,
                "ticket_number": ticket.ticket_number,
            },
        )

    def _actor_role_ids(self, actor: ResolvedCrmSession) -> set[str]:
        role_ids: set[str] = set()
        for assignment in actor.crm_user.assigned_roles:
            role = assignment.role
            if role is None or not role.is_active:
                continue
            if not self._is_operational_role(role.role_key):
                continue
            role_ids.add(role.crm_role_id)
        return role_ids

    def _is_operational_role(self, role_key: str | None) -> bool:
        normalized = self._normalize_role_key(role_key)
        return normalized in self.OPERATIONAL_ROLE_KEYS

    def _notify_ticket_unassigned_to_tecnicos(self, ticket: Ticket) -> None:
        if self._notification_service is None or ticket.assigned_user_id is not None:
            return

        tecnico_ids = self._notification_service.resolve_users_with_role_key("tecnico")
        self._notification_service.notify_bulk(
            recipient_crm_user_ids=tecnico_ids,
            notification_type=NotificationType.TICKET_UNASSIGNED_IN_ROLE,
            title=f"Ticket {ticket.ticket_number} sin asignar",
            body="Hay un ticket pendiente de toma para técnicos de campo.",
            entity_type=NotificationEntityType.TICKET,
            entity_id=ticket.ticket_id,
        )

    def _resolve_notification_recipients_for_event(
        self,
        *,
        event_code: str,
        assigned_user_id: str | None,
        actor_crm_user_id: str,
    ) -> list[str]:
        if self._notification_service is None:
            return []

        rule = self._ticket_repository.session.scalar(
            select(NotificationRule).where(
                NotificationRule.event_code == event_code,
                NotificationRule.is_active.is_(True),
            )
        )
        if rule is None:
            return []

        recipients: set[str] = set()
        if rule.notify_assigned and assigned_user_id:
            recipients.add(assigned_user_id)

        for role_key in rule.notify_roles_json or []:
            recipients.update(self._notification_service.resolve_users_with_role_key(role_key))

        recipients.discard(actor_crm_user_id)
        return list(recipients)

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

    def _log_event(self, event_code: str, actor: ResolvedCrmSession, ticket: Ticket, extra: dict[str, object]) -> None:
        if self._activity_log_service is None:
            return
        self._activity_log_service.log(
            event_code,
            actor,
            entity_type="ticket",
            entity_id=ticket.ticket_id,
            entity_label=ticket.ticket_number,
            summary=event_code,
            extra=extra,
        )
