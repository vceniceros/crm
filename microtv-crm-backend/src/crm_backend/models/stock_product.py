"""Modelo ORM de productos de depósito."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import re
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.core.exceptions import InsufficientStockError, InvalidStockQuantityError, StockProductInactiveError
from crm_backend.db.base import Base
from crm_backend.models.stock_level import StockLevel
from crm_backend.models.stock_movement import StockMovement, StockMovementType


class StockProduct(Base):
    """Representa un producto administrado por el módulo de depósito.

    Attributes:
        product_id: Identificador UUID interno.
        name: Nombre comercial del producto.
        stock_category_id: Categoría asociada.
        image_url: Imagen opcional para la UI.
        current_stock: Stock disponible actual.
        is_active: Indica si el producto admite operaciones.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
        category: Categoría asociada.
        movements: Movimientos registrados del producto.
    """

    __tablename__ = "inventory_products"

    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_categories.category_id"), index=True)
    product_name: Mapped[str] = mapped_column(String(255), index=True)
    product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_of_measure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    shelf_id: Mapped[str | None] = mapped_column(String(1), nullable=True)
    shelf_height: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    requires_tracking: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped[StockCategory] = relationship("StockCategory", back_populates="products", lazy="joined")
    stock_entries: Mapped[list[StockLevel]] = relationship(
        "StockLevel",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="StockMovement.created_at.desc()",
        lazy="selectin",
    )

    @property
    def stock_product_id(self) -> str:
        return self.product_id

    @property
    def visible_product_code(self) -> str:
        if self.product_code:
            return self.product_code
        return f"PRD-{self.product_id[:8].upper()}"

    @property
    def name(self) -> str:
        return self.product_name

    @property
    def stock_category_id(self) -> str | None:
        return self.category_id

    @property
    def primary_stock(self) -> StockLevel | None:
        return self.stock_entries[0] if self.stock_entries else None

    @property
    def current_stock(self) -> int:
        return int(self.primary_stock.quantity_available) if self.primary_stock is not None else 0

    @classmethod
    def create(
        cls,
        *,
        name: str,
        product_code: str,
        stock_category_id: str,
        initial_stock: int,
        image_url: str | None,
        requires_tracking: bool,
        actor_crm_user_id: str | None,
        warehouse_id: str,
        minimum_stock: int = 3,
    ) -> "StockProduct":
        """Construye un producto listo para persistir.

        Args:
            name: Nombre del producto.
            product_code: Código visible del producto.
            stock_category_id: Categoría asociada.
            initial_stock: Stock inicial.
            image_url: URL opcional de imagen.
            actor_crm_user_id: Usuario CRM que crea el producto.
            warehouse_id: Depósito donde se registra el stock inicial.

        Returns:
            StockProduct: Producto instanciado.
        """

        product = cls(
            product_name=name.strip(),
            category_id=stock_category_id,
            product_code=product_code.strip().upper(),
            image_url=image_url,
            minimum_stock=minimum_stock,
            unit_of_measure="unidad",
            requires_tracking=requires_tracking,
            is_active=True,
        )
        product.stock_entries.append(StockLevel.create(warehouse_id=warehouse_id, quantity_available=0))
        if initial_stock > 0:
            product._apply_movement(
                movement_type=StockMovementType.INITIAL_LOAD,
                quantity=initial_stock,
                actor_crm_user_id=actor_crm_user_id,
                warehouse_id=warehouse_id,
            )
        return product

    def increase_stock(
        self,
        *,
        quantity: int,
        actor_crm_user_id: str | None,
        warehouse_id: str,
        reference_entity_type: str | None = None,
        reference_entity_id: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Incrementa el stock actual del producto.

        Args:
            quantity: Cantidad a sumar.
            actor_crm_user_id: Usuario CRM que ejecuta el cambio.
            warehouse_id: Depósito afectado.
        """

        self._apply_movement(
            movement_type=StockMovementType.INCREASE,
            quantity=quantity,
            actor_crm_user_id=actor_crm_user_id,
            warehouse_id=warehouse_id,
            reference_entity_type=reference_entity_type,
            reference_entity_id=reference_entity_id,
            notes=notes,
        )

    def decrease_stock(
        self,
        *,
        quantity: int,
        actor_crm_user_id: str | None,
        warehouse_id: str,
        reference_entity_type: str | None = None,
        reference_entity_id: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Reduce el stock actual del producto.

        Args:
            quantity: Cantidad a descontar.
            actor_crm_user_id: Usuario CRM que ejecuta el cambio.
            warehouse_id: Depósito afectado.
        """

        self._apply_movement(
            movement_type=StockMovementType.DECREASE,
            quantity=quantity,
            actor_crm_user_id=actor_crm_user_id,
            warehouse_id=warehouse_id,
            reference_entity_type=reference_entity_type,
            reference_entity_id=reference_entity_id,
            notes=notes,
        )

    def deactivate(self) -> None:
        """Da de baja lógica al producto para ocultarlo del depósito."""

        self._ensure_active()
        self.is_active = False
        self.deleted_at = datetime.now(UTC)

    def _apply_movement(
        self,
        *,
        movement_type: StockMovementType,
        quantity: int,
        actor_crm_user_id: str | None,
        warehouse_id: str,
        reference_entity_type: str | None = None,
        reference_entity_id: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Aplica un movimiento y actualiza el stock del producto.

        Args:
            movement_type: Tipo de movimiento.
            quantity: Cantidad ajustada.
            actor_crm_user_id: Usuario CRM que ejecuta el cambio.
            warehouse_id: Depósito afectado.
        """

        self._ensure_active()
        if quantity <= 0:
            raise InvalidStockQuantityError()

        stock_entry = self.primary_stock
        if stock_entry is None:
            stock_entry = StockLevel.create(warehouse_id=warehouse_id, quantity_available=0)
            self.stock_entries.append(stock_entry)

        previous_stock = int(stock_entry.quantity_available)
        if movement_type == StockMovementType.DECREASE and previous_stock < quantity:
            raise InsufficientStockError()

        if movement_type == StockMovementType.DECREASE:
            new_stock = previous_stock - quantity
        else:
            new_stock = previous_stock + quantity

        stock_entry.quantity_available = Decimal(new_stock)
        self.movements.append(
            StockMovement.create(
                movement_type=movement_type,
                quantity=quantity,
                actor_crm_user_id=actor_crm_user_id,
                warehouse_id=warehouse_id,
                reference_entity_type=reference_entity_type,
                reference_entity_id=reference_entity_id,
                notes=notes,
            )
        )

    def _ensure_active(self) -> None:
        """Valida que el producto siga operativo."""

        if not self.is_active:
            raise StockProductInactiveError()

    @staticmethod
    def _build_product_code(*, name: str) -> str:
        normalized = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")
        base_code = normalized[:18] or "PRODUCTO"
        return f"PRD-{base_code}-{str(uuid4())[:6].upper()}"