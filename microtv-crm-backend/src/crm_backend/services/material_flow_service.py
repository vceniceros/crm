"""Facades and strategies for task materials and inventory request flows."""

from __future__ import annotations

from dataclasses import dataclass
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
    InventoryDispatch,
    InventoryDispatchItem,
    InventoryRequest,
    InventoryRequestItem,
    InventoryRequestStatus,
    InventorySourceType,
    StockProduct,
    Task,
    TaskAuditEvent,
    TaskRequiredMaterial,
    TemplateMaterial,
)
from crm_backend.repositories import InventoryFlowRepository, StockProductRepository, TaskRepository
from crm_backend.schemas.material_flow import (
    ConfirmDispatchItemRequest,
    CreateInventoryRequestRequest,
    CreateTaskDispatchRequest,
    ReviewInventoryRequestRequest,
)
from crm_backend.schemas.tasks import CreateTaskTemplateRequest, UpdateTaskTemplateRequest
from crm_backend.services.auth_service import ResolvedCrmSession


@dataclass(slots=True)
class DispatchValidationContext:
    product: StockProduct
    quantity_dispatched: int
    serial_number: str | None
    barcode_value: str | None


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
    ) -> None:
        self._task_repository = task_repository
        self._product_repository = product_repository
        self._inventory_flow_repository = inventory_flow_repository
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
        self._ensure_task_is_operable_by_actor(actor, task)
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
            self._ensure_task_is_operable_by_actor(actor, task)
            task.audit_events.append(
                TaskAuditEvent(
                    event_type=f"task.material_{payload.confirmation_type}_confirmed",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"dispatch_item_id": item.dispatch_item_id, "dispatch_id": dispatch.dispatch_id},
                )
            )
            return self._task_repository.save(task)

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
            product.decrease_stock(
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
        if request.request_status != InventoryRequestStatus.APPROVED.value:
            raise InventoryFlowValidationError("Solo se puede despachar una solicitud aprobada.")

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
        if task.current_assigned_crm_user_id != actor.crm_user.crm_user_id:
            raise TaskAccessDeniedError("La tarea solo puede ser operada por el usuario actualmente asignado.")

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
    ) -> None:
        self._task_repository = task_repository
        self._product_repository = product_repository
        self._inventory_flow_repository = inventory_flow_repository
        self._task_material_flow = task_material_flow

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
            task.audit_events.append(
                TaskAuditEvent(
                    event_type="task.inventory_request_created",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"request_id": request.request_id, "items": [item.product_id for item in request.items]},
                )
            )
            self._task_repository.save(task)
            return self._inventory_flow_repository.get_request_by_id(request.request_id) or request
        return self._inventory_flow_repository.save_request(request)

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

        request.request_status = payload.status
        request.review_notes = (payload.review_notes or "").strip() or None
        request.reviewed_by_crm_user_id = actor.crm_user.crm_user_id
        request.reviewed_at = datetime.now(UTC)

        if request.task_id:
            task = self._task_material_flow._get_visible_task(actor, request.task_id)
            self._task_material_flow._ensure_task_is_operable_by_actor(actor, task)
            task.audit_events.append(
                TaskAuditEvent(
                    event_type="task.inventory_request_reviewed",
                    actor_crm_user_id=actor.crm_user.crm_user_id,
                    payload_json={"request_id": request.request_id, "status": request.request_status},
                )
            )
            self._task_repository.save(task)
            return self._inventory_flow_repository.get_request_by_id(request.request_id) or request
        return self._inventory_flow_repository.save_request(request)

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
        if request.request_status != InventoryRequestStatus.APPROVED.value:
            raise InventoryFlowValidationError("La solicitud debe estar aprobada antes de registrar el despacho.")

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
        return self._inventory_flow_repository.save_request(request).dispatches[0]

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
        self._ensure_request_review_access(actor)
        return self._inventory_flow_repository.list_open_requests()

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