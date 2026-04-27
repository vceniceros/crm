"""Modelo ORM de movimientos simples de stock."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class StockMovementType(StrEnum):
    """Enumera los tipos mínimos de movimiento soportados."""

    INITIAL_LOAD = "IN"
    INCREASE = "IN"
    DECREASE = "OUT"


class StockMovement(Base):
    """Representa un ajuste simple de stock sobre un producto.

    Attributes:
        movement_id: Identificador interno del movimiento.
        product_id: Producto afectado.
        movement_type: Tipo de ajuste aplicado.
        quantity: Cantidad movida.
        actor_crm_user_id: Usuario CRM que ejecutó la operación.
        created_at: Fecha de creación.
        product: Producto asociado.
    """

    __tablename__ = "inventory_movements"

    movement_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("warehouses.warehouse_id"))
    movement_type: Mapped[str] = mapped_column(String(30), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reference_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_entity_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_crm_user_id: Mapped[str | None] = mapped_column("performed_by_crm_user_id", Uuid(as_uuid=False), index=True)
    created_at: Mapped[datetime] = mapped_column("performed_at", DateTime(timezone=True), server_default=func.now(), index=True)

    product: Mapped[StockProduct] = relationship("StockProduct", back_populates="movements")

    @classmethod
    def create(
        cls,
        *,
        movement_type: StockMovementType,
        quantity: int,
        actor_crm_user_id: str | None,
        warehouse_id: str,
        reference_entity_type: str | None = None,
        reference_entity_id: str | None = None,
        notes: str | None = None,
    ) -> "StockMovement":
        """Construye un movimiento listo para persistir.

        Args:
            movement_type: Tipo de movimiento.
            quantity: Cantidad ajustada.
            actor_crm_user_id: Usuario CRM que ejecuta el cambio.
            warehouse_id: Depósito afectado por el movimiento.

        Returns:
            StockMovement: Movimiento instanciado.
        """

        return cls(
            movement_type=movement_type.value,
            warehouse_id=warehouse_id,
            quantity=Decimal(quantity),
            reference_entity_type=reference_entity_type,
            reference_entity_id=reference_entity_id,
            notes=notes,
            actor_crm_user_id=actor_crm_user_id,
        )