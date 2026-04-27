"""Facades and strategies for task materials and inventory request flows."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from datetime import UTC, datetime
from uuid import uuid4

from crm_backend.core.exceptions import (
    InventoryAccessDeniedError,
    InventoryDispatchItemNotFoundError,
    InventoryFlowValidationError,
    InventoryRequestNotFoundError,
    StockProductNotFoundError,
    TaskAccessDeniedError,
    TaskNotFoundError,
)
from crm_backend.models import (
    CrmRole,
    CrmUser,
    InventoryDispatch,
    InventoryDispatchItem,
    InventoryRequest,
    InventoryRequestItem,
    InventoryRequestStatus,
    InventorySourceType,
    StockProduct,
    SubtaskStatus,
    Task,
    TaskAuditEvent,
    TaskStatus,
    TaskRequiredMaterial,
    TemplateMaterial,
    Ticket,
    TicketAssignmentHistory,
    TicketAuditEvent,
)
from crm_backend.repositories import CrmRoleRepository, CrmUserRepository, InventoryFlowRepository, StockProductRepository, TaskRepository, TicketRepository
from crm_backend.schemas.material_flow import (
    ConfirmDispatchItemRequest,
    CreateInventoryRequestRequest,
    CreateTaskDispatchRequest,
    ReviewInventoryRequestRequest,
)
from crm_backend.schemas.tasks import CreateTaskTemplateRequest, UpdateTaskTemplateRequest
from crm_backend.services.auth_service import ResolvedCrmSession
from crm_backend.services.notification_service import NotificationService
from crm_backend.models.notification import NotificationEntityType, NotificationType


@dataclass(slots=True)
class DispatchValidationContext:
    product: StockProduct
    quantity_dispatched: int
    serial_number: str | None
    barcode_value: str | None


_logger = logging.getLogger(__name__)


class DispatchValidationStrategy:
    """Validate dispatch item requirements according to product tracking rules."""

    def validate(self, context: DispatchValidationContext) -> None:
        raise NotImplementedError


class GenericDispatchValidationStrategy(DispatchValidationStrategy):
    """Allow generic materials without unit tracking."""

    def validate(self, context: DispatchValidationContext) -> None:
        if context.quantity_dispatched <= 0:
            raise InventoryFlowValidationError("La cantidad despachada debe ser mayor a cero.")


class TrackingRequiredDispatchValidationStrategy(DispatchValidationStrategy):
    """Enforce unit-level tracking for tracked equipment."""

    def validate(self, context: DispatchValidationContext) -> None:
        if context.quantity_dispatched != 1:
            raise InventoryFlowValidationError(
                "Los productos con tracking unitario deben despacharse de a una unidad por registro."
            )
        if not (context.serial_number or context.barcode_value):
            raise InventoryFlowValidationError(
                "El producto requiere serial o código de barras para registrar el despacho real."
            )


class DispatchValidationStrategyRegistry:
    """Resolve the validation strategy for a dispatched product."""

    def __init__(self) -> None:
        self._tracked_strategy = TrackingRequiredDispatchValidationStrategy()
        self._generic_strategy = GenericDispatchValidationStrategy()

    def get(self, product: StockProduct) -> DispatchValidationStrategy:
        return self._tracked_strategy if product.requires_tracking else self._generic_strategy


class TaskMaterialFlowFacade:
    """Encapsulate template requirements, direct task dispatches, and confirmations."""

    def __init__(
        self,
        task_repository: TaskRepository,
        product_repository: StockProductRepository,
        inventory_flow_repository: InventoryFlowRepository,
        ticket_repository: TicketRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._product_repository = product_repository
        self._inventory_flow_repository = inventory_flow_repository
        self._ticket_repository = ticket_repository
        self._notification_service = notification_service
        self._dispatch_strategy_registry = DispatchValidationStrategyRegistry()

    def sync_template_materials(
        self,
        template,
        payload: CreateTaskTemplateRequest | UpdateTaskTemplateRequest,
    ) -> None:
        template.required_materials.clear()
        seen_product_ids: set[str] = set()
        for material_payload in payload.required_materials:
            if material_payload.product_id in seen_product_ids:
                raise InventoryFlowValidationError("No se puede repetir el mismo producto en los materiales requeridos del template.")
            product = self._get_active_product(material_payload.product_id)
            seen_product_ids.add(product.product_id)
            template.required_materials.append(
                TemplateMaterial(
                    product_id=product.product_id,
                    quantity_required=material_payload.quantity_required,
                    notes=(material_payload.notes or "").strip() or None,
                )
            )

    def materialize_task_requirements(self, task: Task, template) -> None:
        task.required_materials.clear()
        for required_material in template.required_materials:
            task.required_materials.append(
                TaskRequiredMaterial(
                    template_material_id=required_material.template_material_id,
                    product_id=required_material.product_id,
                    quantity_required=required_material.quantity_required,
                    notes=required_material.notes,
                )
            )

    def create_task_dispatch(
        self,
        actor: ResolvedCrmSession,
        task_id: str,
        payload: CreateTaskDispatchRequest,
    ) -> Task:
        self._ensure_dispatch_write_access(actor)
        task = self._get_visible_task(actor, task_id)
        warehouse_id = self._product_repository.get_default_warehouse_id()
        dispatch = InventoryDispatch(
            dispatch_id=str(uuid4()),
            source_type=InventorySourceType.TASK.value,
            task_id=task.task_id,
            request_id=payload.request_id,
            dispatched_by_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=warehouse_id,
            dispatch_notes=(payload.dispatch_notes or "").strip() or None,
        )
        self._validate_request_belongs_to_task(payload.request_id, task.task_id)
        self._populate_dispatch_items(
            actor=actor,
            dispatch=dispatch,
            items_payload=payload.items,
            warehouse_id=warehouse_id,
            reference_entity_type="TASK_DISPATCH",
        )
        task.dispatches.append(dispatch)
        task.audit_events.append(
            TaskAuditEvent(
                event_type="task.material_dispatch_created",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "dispatch_id": dispatch.dispatch_id,
                    "request_id": dispatch.request_id,
                    "items": [item.product_id for item in dispatch.items],
                },
            )
        )

        if dispatch.request_id:
            linked_request = next((request for request in task.inventory_requests if request.request_id == dispatch.request_id), None)
            if linked_request is not None:
                linked_request.request_status = InventoryRequestStatus.PENDING_RECEIPT.value

        self.sync_task_block_status(task)
        return self._task_repository.save(task)

    def confirm_dispatch_item(
        self,
        actor: ResolvedCrmSession,
        dispatch_item_id: str,
        payload: ConfirmDispatchItemRequest,
    ) -> Task | InventoryDispatch:
        self._ensure_technician_confirmation_access(actor)
        item = self._inventory_flow_repository.get_dispatch_item_by_id(dispatch_item_id)
        if item is None:
            raise InventoryDispatchItemNotFoundError()

        dispatch = item.dispatch
        timestamp = datetime.now(UTC)
        if payload.confirmation_type == "received":
            if dispatch.request_id:
                self._ensure_request_receipt_confirmation_access(actor, dispatch.request_id)
            item.received_confirmed_by_crm_user_id = actor.crm_user.crm_user_id
            item.received_confirmed_at = timestamp
        elif payload.confirmation_type == "delivered":
            item.delivered_confirmed_by_crm_user_id = actor.crm_user.crm_user_id
            item.delivered_confirmed_at = timestamp
        else:
            item.installed_confirmed_by_crm_user_id = actor.crm_user.crm_user_id
            item.installed_confirmed_at = timestamp

        if dispatch.task_id:
            task = self._get_visible_task(actor, dispatch.task_id)
            if payload.confirmation_type != "received" or not dispatch.request_id:
                self._ensure_task_is_operable_by_actor(actor, task)

            if dispatch.request_id and payload.confirmation_type == "received":
                linked_request = next((request for request in task.inventory_requests if request.request_id == dispatch.request_id), None)
                if linked_request is not None and self._is_request_fully_received(linked_request):
                    linked_request.request_status = InventoryRequestStatus.COMPLETED.value

            self.sync_task_block_status(task)
            task.audit_events.append(
                TaskAuditEvent(
                    event_type=f"task.material_{payload.confirmation_type}_confirmed",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"dispatch_item_id": item.dispatch_item_id, "dispatch_id": dispatch.dispatch_id},
                )
            )
            return self._task_repository.save(task)

        if payload.confirmation_type == "received" and dispatch.request_id:
            linked_request = self._inventory_flow_repository.get_request_by_id(dispatch.request_id)
            if linked_request is not None and self._is_request_fully_received(linked_request):
                transitioned_to_completed = linked_request.request_status != InventoryRequestStatus.COMPLETED.value
                if transitioned_to_completed:
                    linked_request.request_status = InventoryRequestStatus.COMPLETED.value
                dispatch.received_by_crm_user_id = actor.crm_user.crm_user_id
                dispatch.received_at = timestamp
                reception_comment = (payload.reception_comment or "").strip() or None
                dispatch.reception_comment = reception_comment

                ticket = self._ticket_repository.get_ticket_detail(linked_request.external_ticket_id or "") if linked_request.external_ticket_id else None
                if transitioned_to_completed and ticket is not None:
                    ticket.audit_events.append(
                        TicketAuditEvent(
                            event_type="ticket.dispatch_received_confirmed",
                            actor_crm_user_id=actor.crm_user.crm_user_id,
                            payload_json={
                                "request_id": linked_request.request_id,
                                "dispatch_id": dispatch.dispatch_id,
                                "reception_comment": reception_comment,
                            },
                        )
                    )
                    self._ticket_repository.save(ticket)

                self._inventory_flow_repository.save_request(linked_request)
                try:
                    if transitioned_to_completed and self._notification_service is not None and linked_request.requested_by_crm_user_id is not None:
                        self._notification_service.notify(
                            recipient_crm_user_id=linked_request.requested_by_crm_user_id,
                            notification_type=NotificationType.DEPOSIT_REQUEST_RECEIVED,
                            title="Recepción de materiales confirmada",
                            body="La recepción de todos los materiales de tu solicitud fue confirmada.",
                            entity_type=NotificationEntityType.DEPOSIT_REQUEST,
                            entity_id=linked_request.request_id,
                        )
                except Exception:
                    _logger.exception("Error sending confirm_dispatch_item notification")

        return self._inventory_flow_repository.save_dispatch(dispatch)

    def _populate_dispatch_items(
        self,
        *,
        actor: ResolvedCrmSession,
        dispatch: InventoryDispatch,
        items_payload,
        warehouse_id: str,
        reference_entity_type: str,
    ) -> None:
        for item_payload in items_payload:
            product = self._get_active_product(item_payload.product_id)
            strategy = self._dispatch_strategy_registry.get(product)
            strategy.validate(
                DispatchValidationContext(
                    product=product,
                    quantity_dispatched=item_payload.quantity_dispatched,
                    serial_number=(item_payload.serial_number or "").strip() or None,
                    barcode_value=(item_payload.barcode_value or "").strip() or None,
                )
            )
            product.increase_stock(
                quantity=item_payload.quantity_dispatched,
                actor_crm_user_id=actor.crm_user.crm_user_id,
                warehouse_id=warehouse_id,
                reference_entity_type=reference_entity_type,
                reference_entity_id=dispatch.dispatch_id,
                notes=(item_payload.notes or dispatch.dispatch_notes or "").strip() or None,
            )
            dispatch.items.append(
                InventoryDispatchItem(
                    dispatch_item_id=str(uuid4()),
                    product_id=product.product_id,
                    quantity_dispatched=item_payload.quantity_dispatched,
                    serial_number=(item_payload.serial_number or "").strip() or None,
                    barcode_value=(item_payload.barcode_value or "").strip() or None,
                    notes=(item_payload.notes or "").strip() or None,
                )
            )

    def _validate_request_belongs_to_task(self, request_id: str | None, task_id: str) -> None:
        if request_id is None:
            return
        request = self._inventory_flow_repository.get_request_by_id(request_id)
        if request is None or request.task_id != task_id:
            raise InventoryFlowValidationError("La solicitud indicada no corresponde a la tarea actual.")
        if request.request_status not in {InventoryRequestStatus.APPROVED.value, InventoryRequestStatus.PENDING_DISPATCH.value}:
            raise InventoryFlowValidationError("Solo se puede despachar una solicitud en pendiente de despacho.")

    def _get_visible_task(self, actor: ResolvedCrmSession, task_id: str) -> Task:
        task = self._task_repository.get_task_detail(task_id)
        if task is None:
            raise TaskNotFoundError()
        if "admin" in actor.role_keys or "ejecutivo" in actor.role_keys:
            return task
        actor_id = actor.crm_user.crm_user_id
        if any(
            subtask.assigned_crm_user_id == actor_id or subtask.responsible_role_key in actor.role_keys
            for subtask in task.subtasks
        ):
            return task
        raise TaskAccessDeniedError("El usuario no puede operar la tarea indicada.")
    def _ensure_task_is_operable_by_actor(self, actor: ResolvedCrmSession, task: Task) -> None:
        if "admin" in actor.role_keys:
            return
        if task.current_assigned_crm_user_id != actor.crm_user.crm_user_id:
            raise TaskAccessDeniedError("La tarea solo puede ser operada por el usuario actualmente asignado.")

    def sync_task_block_status(self, task: Task) -> None:
        blocking_statuses = {
            InventoryRequestStatus.PENDING.value,
            InventoryRequestStatus.PENDING_DISPATCH.value,
            InventoryRequestStatus.PENDING_RECEIPT.value,
            InventoryRequestStatus.APPROVED.value,
        }
        has_blocking_requests = any(request.request_status in blocking_statuses for request in task.inventory_requests)
        if has_blocking_requests:
            task.status = TaskStatus.BLOCKED.value
            return

        # Keep blocked state when the task already finished all subtasks and is waiting executive approval.
        if task.status == TaskStatus.BLOCKED.value and all(subtask.status == SubtaskStatus.COMPLETED.value for subtask in task.subtasks):
            return

        if task.status not in {TaskStatus.COMPLETED.value, TaskStatus.PENDING_APPROVAL.value}:
            task.status = TaskStatus.IN_PROGRESS.value

    def _is_request_fully_received(self, request: InventoryRequest) -> bool:
        dispatch_items = [item for dispatch in request.dispatches for item in dispatch.items]
        if not dispatch_items:
            return False
        return all(item.received_confirmed_at is not None for item in dispatch_items)

    def _ensure_request_receipt_confirmation_access(self, actor: ResolvedCrmSession, request_id: str) -> None:
        request = self._inventory_flow_repository.get_request_by_id(request_id)
        if request is None:
            raise InventoryRequestNotFoundError()
        if "admin" in actor.role_keys:
            return
        if request.requested_by_crm_user_id != actor.crm_user.crm_user_id:
            raise InventoryAccessDeniedError("Solo quien creó la solicitud puede confirmar el recibimiento.")

    def _get_active_product(self, product_id: str) -> StockProduct:
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            raise StockProductNotFoundError()
        product._ensure_active()
        return product

    def _ensure_dispatch_write_access(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "deposito" in actor.role_keys:
            return
        raise InventoryAccessDeniedError("Solo depósito puede registrar despachos reales.")

    def _ensure_technician_confirmation_access(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "tecnico" in actor.role_keys:
            return
        raise InventoryAccessDeniedError("Solo un técnico puede confirmar recepción, entrega o instalación.")


class InventoryRequestFacade:
    """Encapsulate additional inventory requests and request-driven dispatches."""

    def __init__(
        self,
        task_repository: TaskRepository,
        product_repository: StockProductRepository,
        inventory_flow_repository: InventoryFlowRepository,
        task_material_flow: TaskMaterialFlowFacade,
        ticket_repository: TicketRepository,
        role_repository: CrmRoleRepository,
        user_repository: CrmUserRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._task_repository = task_repository
        self._product_repository = product_repository
        self._inventory_flow_repository = inventory_flow_repository
        self._task_material_flow = task_material_flow
        self._ticket_repository = ticket_repository
        self._role_repository = role_repository
        self._user_repository = user_repository
        self._notification_service = notification_service

    def create_request(self, actor: ResolvedCrmSession, payload: CreateInventoryRequestRequest) -> InventoryRequest:
        self._ensure_request_create_access(actor)
        source_type = payload.source_type
        task_id = payload.task_id
        external_ticket_id = (payload.external_ticket_id or "").strip() or None
        if source_type == InventorySourceType.TASK.value:
            if not task_id:
                raise InventoryFlowValidationError("La solicitud de tarea requiere un task_id.")
            task = self._task_material_flow._get_visible_task(actor, task_id)
            self._task_material_flow._ensure_task_is_operable_by_actor(actor, task)
        else:
            task = None
            if not external_ticket_id:
                raise InventoryFlowValidationError("La solicitud de ticket requiere un identificador de ticket.")
            ticket = self._ticket_repository.get_ticket_detail(external_ticket_id)
            if ticket is None:
                raise InventoryFlowValidationError("No se encontró el ticket asociado para registrar la solicitud.")
            self._ensure_ticket_is_operable_by_actor(actor, ticket)

        request = InventoryRequest(
            request_id=str(uuid4()),
            source_type=source_type,
            task_id=task_id if source_type == InventorySourceType.TASK.value else None,
            external_ticket_id=external_ticket_id if source_type == InventorySourceType.TICKET.value else None,
            request_reason=(payload.request_reason or "").strip() or None,
            requested_by_crm_user_id=actor.crm_user.crm_user_id,
        )
        seen_product_ids: set[str] = set()
        for item_payload in payload.items:
            product = self._task_material_flow._get_active_product(item_payload.product_id)
            if product.product_id in seen_product_ids:
                raise InventoryFlowValidationError("No se puede repetir el mismo producto dentro de una solicitud adicional.")
            seen_product_ids.add(product.product_id)
            request.items.append(
                InventoryRequestItem(
                    request_item_id=str(uuid4()),
                    product_id=product.product_id,
                    quantity_requested=item_payload.quantity_requested,
                    notes=(item_payload.notes or "").strip() or None,
                )
            )

        if task is not None:
            task.inventory_requests.append(request)
            self._task_material_flow.sync_task_block_status(task)
            task.audit_events.append(
                TaskAuditEvent(
                    event_type="task.inventory_request_created",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"request_id": request.request_id, "items": [item.product_id for item in request.items]},
                )
            )
            self._task_repository.save(task)
            return self._inventory_flow_repository.get_request_by_id(request.request_id) or request
        persisted_request = self._inventory_flow_repository.save_request(request)
        self._auto_assign_ticket_to_deposito(actor, persisted_request)
        try:
            if self._notification_service is not None:
                deposito_user_ids = self._notification_service.resolve_users_with_role_key("deposito")
                self._notification_service.notify_bulk(
                    recipient_crm_user_ids=list(set(deposito_user_ids) - {actor.crm_user.crm_user_id}),
                    notification_type=NotificationType.DEPOSIT_REQUEST_CREATED,
                    title="Nueva solicitud de depósito",
                    body="Se creó una nueva solicitud de materiales para revisión.",
                    entity_type=NotificationEntityType.DEPOSIT_REQUEST,
                    entity_id=persisted_request.request_id,
                )
        except Exception:
            _logger.exception("Error sending create_request notification for request %s", persisted_request.request_id)
        return persisted_request

    def review_request(
        self,
        actor: ResolvedCrmSession,
        request_id: str,
        payload: ReviewInventoryRequestRequest,
    ) -> InventoryRequest:
        self._ensure_request_review_access(actor)
        request = self._inventory_flow_repository.get_request_by_id(request_id)
        if request is None:
            raise InventoryRequestNotFoundError()
        if request.request_status != InventoryRequestStatus.PENDING.value:
            raise InventoryFlowValidationError("Solo se pueden revisar solicitudes pendientes.")

        review_notes = (payload.review_notes or "").strip() or None
        if payload.status == "REJECTED" and not review_notes:
            raise InventoryFlowValidationError("El rechazo de solicitud requiere un comentario obligatorio.")

        if payload.status == "APPROVED":
            request.request_status = InventoryRequestStatus.PENDING_DISPATCH.value
        else:
            request.request_status = InventoryRequestStatus.REJECTED.value
        request.review_notes = review_notes
        request.reviewed_by_crm_user_id = actor.crm_user.crm_user_id
        request.reviewed_at = datetime.now(UTC)

        if request.task_id:
            task = self._task_material_flow._get_visible_task(actor, request.task_id)
            self._task_material_flow.sync_task_block_status(task)
            task.audit_events.append(
                TaskAuditEvent(
                    event_type="task.inventory_request_reviewed",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"request_id": request.request_id, "status": request.request_status},
                )
            )
            self._task_repository.save(task)
            return self._inventory_flow_repository.get_request_by_id(request.request_id) or request
        persisted_request = self._inventory_flow_repository.save_request(request)
        try:
            if self._notification_service is not None and persisted_request.requested_by_crm_user_id is not None:
                notif_type = (
                    NotificationType.DEPOSIT_REQUEST_APPROVED
                    if persisted_request.request_status == InventoryRequestStatus.PENDING_DISPATCH.value
                    else NotificationType.DEPOSIT_REQUEST_REJECTED
                )
                status_text = "aprobada" if notif_type == NotificationType.DEPOSIT_REQUEST_APPROVED else "rechazada"
                self._notification_service.notify(
                    recipient_crm_user_id=persisted_request.requested_by_crm_user_id,
                    notification_type=notif_type,
                    title=f"Solicitud de depósito {status_text}",
                    body=f"Tu solicitud de materiales fue {status_text} por el depósito.",
                    entity_type=NotificationEntityType.DEPOSIT_REQUEST,
                    entity_id=persisted_request.request_id,
                )
        except Exception:
            _logger.exception("Error sending review_request notification for request %s", persisted_request.request_id)
        if persisted_request.request_status == InventoryRequestStatus.REJECTED.value:
            self._auto_assign_ticket_to_requester(
                actor,
                persisted_request,
                reason="inventory_request_rejected",
                note="Reasignación automática al solicitante por rechazo de depósito.",
            )
        return persisted_request

    def dispatch_request(
        self,
        actor: ResolvedCrmSession,
        request_id: str,
        payload: CreateTaskDispatchRequest,
    ) -> InventoryDispatch | Task:
        self._ensure_request_review_access(actor)
        request = self._inventory_flow_repository.get_request_by_id(request_id)
        if request is None:
            raise InventoryRequestNotFoundError()
        if request.request_status not in {InventoryRequestStatus.APPROVED.value, InventoryRequestStatus.PENDING_DISPATCH.value}:
            raise InventoryFlowValidationError("La solicitud debe estar en pendiente de despacho antes de registrar el despacho.")

        if request.task_id:
            return self._task_material_flow.create_task_dispatch(
                actor,
                request.task_id,
                CreateTaskDispatchRequest(
                    request_id=request_id,
                    dispatch_notes=payload.dispatch_notes,
                    items=payload.items,
                ),
            )

        warehouse_id = self._product_repository.get_default_warehouse_id()
        dispatch = InventoryDispatch(
            dispatch_id=str(uuid4()),
            source_type=request.source_type,
            external_ticket_id=request.external_ticket_id,
            request_id=request.request_id,
            dispatched_by_crm_user_id=actor.crm_user.crm_user_id,
            warehouse_id=warehouse_id,
            dispatch_notes=(payload.dispatch_notes or "").strip() or None,
        )
        self._task_material_flow._populate_dispatch_items(
            actor=actor,
            dispatch=dispatch,
            items_payload=payload.items,
            warehouse_id=warehouse_id,
            reference_entity_type="TICKET_REQUEST_DISPATCH",
        )
        request.dispatches.append(dispatch)
        request.request_status = InventoryRequestStatus.PENDING_RECEIPT.value
        persisted_request = self._inventory_flow_repository.save_request(request)
        self._auto_assign_ticket_to_requester(
            actor,
            persisted_request,
            reason="inventory_request_dispatched",
            note="Reasignación automática al solicitante luego del despacho.",
        )
        if self._notification_service is not None and persisted_request.requested_by_crm_user_id is not None:
            self._notification_service.notify(
                recipient_crm_user_id=persisted_request.requested_by_crm_user_id,
                notification_type=NotificationType.DEPOSIT_REQUEST_DISPATCHED,
                title="Materiales despachados",
                body="Los materiales de tu solicitud fueron despachados. Confirmá la recepción cuando lleguen.",
                entity_type=NotificationEntityType.DEPOSIT_REQUEST,
                entity_id=persisted_request.request_id,
            )
        try:
            if self._notification_service is not None and persisted_request.requested_by_crm_user_id is not None:
                self._notification_service.notify(
                    recipient_crm_user_id=persisted_request.requested_by_crm_user_id,
                    notification_type=NotificationType.DEPOSIT_REQUEST_DISPATCHED,
                    title="Materiales despachados",
                    body="Los materiales de tu solicitud fueron despachados. Confirmá la recepción cuando lleguen.",
                    entity_type=NotificationEntityType.DEPOSIT_REQUEST,
                    entity_id=persisted_request.request_id,
                )
        except Exception:
            _logger.exception("Error sending dispatch_request notification for request %s", persisted_request.request_id)
        return persisted_request.dispatches[0]

    def list_source_flow(
        self,
        actor: ResolvedCrmSession,
        *,
        source_type: str,
        source_reference_id: str,
    ) -> tuple[list[InventoryRequest], list[InventoryDispatch]]:
        self._ensure_source_read_access(actor, source_type, source_reference_id)
        requests = self._inventory_flow_repository.list_requests_for_source(
            source_type=source_type,
            source_reference_id=source_reference_id,
        )
        dispatches = self._inventory_flow_repository.list_dispatches_for_source(
            source_type=source_type,
            source_reference_id=source_reference_id,
        )
        return requests, dispatches

    def list_open_requests(self, actor: ResolvedCrmSession) -> list[InventoryRequest]:
        self._ensure_request_read_access(actor)
        return self._inventory_flow_repository.list_open_requests()

    def _ensure_request_read_access(self, actor: ResolvedCrmSession) -> None:
        if {"admin", "deposito", "ejecutivo"}.intersection(actor.role_keys):
            return
        raise InventoryAccessDeniedError("Solo depósito, ejecutivo o administrador puede ver solicitudes adicionales.")

    def _ensure_request_create_access(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "tecnico" in actor.role_keys:
            return
        raise InventoryAccessDeniedError("Solo un técnico o administrador puede crear solicitudes adicionales.")

    def _ensure_request_review_access(self, actor: ResolvedCrmSession) -> None:
        if "admin" in actor.role_keys or "deposito" in actor.role_keys:
            return
        raise InventoryAccessDeniedError("Solo depósito puede revisar o despachar solicitudes adicionales.")

    def _ensure_source_read_access(self, actor: ResolvedCrmSession, source_type: str, source_reference_id: str) -> None:
        if source_type == InventorySourceType.TASK.value:
            self._task_material_flow._get_visible_task(actor, source_reference_id)
            return
        if {"admin", "ejecutivo", "deposito", "tecnico"}.intersection(actor.role_keys):
            return
        raise InventoryAccessDeniedError("El usuario no puede consultar solicitudes de inventario para este ticket.")

    def _auto_assign_ticket_to_deposito(self, actor: ResolvedCrmSession, request: InventoryRequest) -> None:
        ticket = self._ticket_for_request(request)
        if ticket is None:
            return

        deposito_role = self._resolve_deposito_role()
        if deposito_role is None:
            return

        previous_role_id = ticket.assigned_role_id
        previous_user_id = ticket.assigned_user_id
        next_role_id = deposito_role.crm_role_id

        if previous_role_id == next_role_id and previous_user_id is None:
            return

        ticket.assigned_role_id = next_role_id
        ticket.assigned_user_id = None
        ticket.assignment_history.append(
            TicketAssignmentHistory(
                previous_role_id=previous_role_id,
                previous_user_id=previous_user_id,
                assigned_role_id=ticket.assigned_role_id,
                assigned_user_id=ticket.assigned_user_id,
                assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                notes="Reasignación automática a depósito por solicitud de materiales.",
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.assignment_changed",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "reason": "inventory_request_created",
                    "request_id": request.request_id,
                    "assigned_role_id": ticket.assigned_role_id,
                    "assigned_user_id": ticket.assigned_user_id,
                },
            )
        )
        self._ticket_repository.save(ticket)

    def _auto_assign_ticket_to_requester(
        self,
        actor: ResolvedCrmSession,
        request: InventoryRequest,
        *,
        reason: str,
        note: str,
    ) -> None:
        ticket = self._ticket_for_request(request)
        if ticket is None:
            return

        requester_user = self._user_repository.get_by_id(request.requested_by_crm_user_id)
        if requester_user is None:
            return

        requester_role = self._resolve_preferred_role_for_user(requester_user)
        previous_role_id = ticket.assigned_role_id
        previous_user_id = ticket.assigned_user_id
        next_role_id = requester_role.crm_role_id if requester_role is not None else ticket.assigned_role_id

        if previous_user_id == requester_user.crm_user_id and previous_role_id == next_role_id:
            return

        ticket.assigned_role_id = next_role_id
        ticket.assigned_user_id = requester_user.crm_user_id
        ticket.assignment_history.append(
            TicketAssignmentHistory(
                previous_role_id=previous_role_id,
                previous_user_id=previous_user_id,
                assigned_role_id=ticket.assigned_role_id,
                assigned_user_id=ticket.assigned_user_id,
                assigned_by_crm_user_id=actor.crm_user.crm_user_id,
                notes=note,
            )
        )
        ticket.audit_events.append(
            TicketAuditEvent(
                event_type="ticket.assignment_changed",
                actor_crm_user_id=actor.crm_user.crm_user_id,
                payload_json={
                    "reason": reason,
                    "request_id": request.request_id,
                    "assigned_role_id": ticket.assigned_role_id,
                    "assigned_user_id": ticket.assigned_user_id,
                },
            )
        )
        self._ticket_repository.save(ticket)

    def _ticket_for_request(self, request: InventoryRequest) -> Ticket | None:
        ticket_id = (request.external_ticket_id or "").strip()
        if not ticket_id:
            return None
        return self._ticket_repository.get_ticket_detail(ticket_id)

    def _ensure_ticket_is_operable_by_actor(self, actor: ResolvedCrmSession, ticket: Ticket) -> None:
        if {"admin", "ejecutivo"}.intersection(actor.role_keys):
            return

        actor_user_id = actor.crm_user.crm_user_id
        actor_role_ids = {
            assignment.crm_role_id
            for assignment in actor.crm_user.assigned_roles
            if assignment.role is not None and assignment.role.is_active
        }
        if ticket.assigned_user_id == actor_user_id:
            return
        if ticket.assigned_user_id is None and ticket.assigned_role_id is not None and ticket.assigned_role_id in actor_role_ids:
            return

        raise InventoryAccessDeniedError("Solo el técnico actualmente operativo puede derivar el ticket a depósito.")

    def _resolve_deposito_role(self) -> CrmRole | None:
        return self._role_repository.get_by_key("encargado_deposito") or self._role_repository.get_by_key("deposito")

    def _resolve_preferred_role_for_user(self, user: CrmUser) -> CrmRole | None:
        role_priority = ["tecnico_campo", "tecnico", "encargado_deposito", "deposito", "ejecutivo", "admin", "admin_crm"]
        role_map: dict[str, CrmRole] = {}
        for assignment in user.assigned_roles:
            role = assignment.role
            if role is None or not role.is_active:
                continue
            role_map[role.role_key] = role

        for key in role_priority:
            if key in role_map:
                return role_map[key]

        return next(iter(role_map.values()), None)