"""ORM models for template materials, field requests, and dispatch flows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class InventorySourceType(StrEnum):
    """Supported source types for field inventory flows."""

    TASK = "TASK"
    TICKET = "TICKET"


class InventoryRequestStatus(StrEnum):
    """Lifecycle states for additional inventory requests."""

    PENDING = "PENDING"
    PENDING_DISPATCH = "PENDING_DISPATCH"
    PENDING_RECEIPT = "PENDING_RECEIPT"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TemplateMaterial(Base):
    """Minimum required material attached to a task template."""

    __tablename__ = "template_materials"
    __table_args__ = (UniqueConstraint("template_id", "product_id", name="template_materials_template_id_product_id_key"),)

    template_material_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    template_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("task_templates.template_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity_required: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped[TaskTemplate] = relationship("TaskTemplate", back_populates="required_materials")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")

    @property
    def required_material_id(self) -> str:
        return self.template_material_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking


class TaskRequiredMaterial(Base):
    """Snapshot of the template requirements copied into a task."""

    __tablename__ = "task_required_materials"

    task_required_material_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id", ondelete="CASCADE"), index=True)
    template_material_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("template_materials.template_material_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity_required: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[Task] = relationship("Task", back_populates="required_materials")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")

    @property
    def required_material_id(self) -> str:
        return self.task_required_material_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking


class TicketRequiredMaterial(Base):
    """Optional material requirements provided during ticket creation."""

    __tablename__ = "ticket_required_materials"

    ticket_required_material_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="required_materials")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")

    @property
    def required_material_id(self) -> str:
        return self.ticket_required_material_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking


class TaskExtraMaterial(Base):
    """Optional extra materials provided during task creation."""

    __tablename__ = "task_extra_materials"

    task_extra_material_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped[Task] = relationship("Task", back_populates="extra_materials")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")

    @property
    def required_material_id(self) -> str:
        return self.task_extra_material_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking


class InventoryRequest(Base):
    """Additional product request created from a task or external ticket."""

    __tablename__ = "inventory_requests"

    request_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    source_type: Mapped[str] = mapped_column(String(20), index=True)
    task_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=True, index=True)
    external_ticket_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    request_status: Mapped[str] = mapped_column(String(30), default=InventoryRequestStatus.PENDING.value, server_default=InventoryRequestStatus.PENDING.value, index=True)
    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    reviewed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task | None] = relationship("Task", back_populates="inventory_requests")
    requested_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[requested_by_crm_user_id], lazy="joined")
    reviewed_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[reviewed_by_crm_user_id], lazy="joined")
    items: Mapped[list[InventoryRequestItem]] = relationship(
        "InventoryRequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="InventoryRequestItem.created_at",
        lazy="selectin",
    )
    dispatches: Mapped[list[InventoryDispatch]] = relationship(
        "InventoryDispatch",
        back_populates="request",
        order_by="InventoryDispatch.created_at.desc()",
        lazy="selectin",
    )

    @property
    def inventory_request_id(self) -> str:
        return self.request_id

    @property
    def source_reference_id(self) -> str:
        return self.task_id or self.external_ticket_id or ""

    @property
    def requested_by_display_name(self) -> str | None:
        return _user_display_label(self.requested_by_user)

    @property
    def reviewed_by_display_name(self) -> str | None:
        return _user_display_label(self.reviewed_by_user)


class InventoryRequestItem(Base):
    """Requested item inside an additional inventory request."""

    __tablename__ = "inventory_request_items"

    request_item_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    request_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_requests.request_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity_requested: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped[InventoryRequest] = relationship("InventoryRequest", back_populates="items")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")

    @property
    def inventory_request_item_id(self) -> str:
        return self.request_item_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking


class InventoryDispatch(Base):
    """Real stock dispatch executed for a task or external ticket."""

    __tablename__ = "inventory_dispatches"

    dispatch_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    source_type: Mapped[str] = mapped_column(String(20), index=True)
    task_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=True, index=True)
    external_ticket_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_requests.request_id", ondelete="SET NULL"), nullable=True, index=True)
    dispatched_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("warehouses.warehouse_id"), index=True)
    dispatch_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reception_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    task: Mapped[Task | None] = relationship("Task", back_populates="dispatches")
    request: Mapped[InventoryRequest | None] = relationship("InventoryRequest", back_populates="dispatches")
    dispatched_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[dispatched_by_crm_user_id], lazy="joined")
    received_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[received_by_crm_user_id], lazy="joined")
    items: Mapped[list[InventoryDispatchItem]] = relationship(
        "InventoryDispatchItem",
        back_populates="dispatch",
        cascade="all, delete-orphan",
        order_by="InventoryDispatchItem.created_at",
        lazy="selectin",
    )

    @property
    def inventory_dispatch_id(self) -> str:
        return self.dispatch_id

    @property
    def source_reference_id(self) -> str:
        return self.task_id or self.external_ticket_id or ""

    @property
    def dispatched_by_display_name(self) -> str | None:
        return _user_display_label(self.dispatched_by_user)

    @property
    def received_by_display_name(self) -> str | None:
        return _user_display_label(self.received_by_user)


class InventoryDispatchItem(Base):
    """Concrete dispatched item, including unit tracking and technician confirmations."""

    __tablename__ = "inventory_dispatch_items"

    dispatch_item_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    dispatch_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_dispatches.dispatch_id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id", ondelete="CASCADE"), index=True)
    quantity_dispatched: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    barcode_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_confirmed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    received_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_confirmed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    delivered_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_confirmed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    installed_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dispatch: Mapped[InventoryDispatch] = relationship("InventoryDispatch", back_populates="items")
    product: Mapped[StockProduct] = relationship("StockProduct", lazy="joined")
    received_confirmed_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[received_confirmed_by_crm_user_id], lazy="joined")
    delivered_confirmed_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[delivered_confirmed_by_crm_user_id], lazy="joined")
    installed_confirmed_by_user: Mapped["CrmUser | None"] = relationship("CrmUser", foreign_keys=[installed_confirmed_by_crm_user_id], lazy="joined")

    @property
    def inventory_dispatch_item_id(self) -> str:
        return self.dispatch_item_id

    @property
    def product_code(self) -> str:
        return self.product.visible_product_code

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def requires_tracking(self) -> bool:
        return self.product.requires_tracking

    @property
    def received_confirmed_by_display_name(self) -> str | None:
        return _user_display_label(self.received_confirmed_by_user)

    @property
    def delivered_confirmed_by_display_name(self) -> str | None:
        return _user_display_label(self.delivered_confirmed_by_user)

    @property
    def installed_confirmed_by_display_name(self) -> str | None:
        return _user_display_label(self.installed_confirmed_by_user)


def _user_display_label(user: object | None) -> str | None:
    if user is None:
        return None
    display_name = getattr(user, "display_name", None)
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    email = getattr(user, "email", None)
    if isinstance(email, str) and email.strip():
        return email.strip()
    return None
