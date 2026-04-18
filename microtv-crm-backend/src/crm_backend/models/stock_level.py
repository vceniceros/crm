"""Modelo ORM del stock actual por producto y depósito."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class StockLevel(Base):
    """Representa el stock actual del producto en un depósito."""

    __tablename__ = "inventory_stock"

    stock_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("warehouses.warehouse_id"), index=True)
    quantity_available: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, server_default="0")
    quantity_reserved: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, server_default="0")
    minimum_stock: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product: Mapped[StockProduct] = relationship("StockProduct", back_populates="stock_entries")
    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="stock_entries")

    @classmethod
    def create(cls, *, warehouse_id: str, quantity_available: int | Decimal) -> "StockLevel":
        """Construye un registro de stock listo para persistir."""

        return cls(warehouse_id=warehouse_id, quantity_available=Decimal(quantity_available), quantity_reserved=Decimal(0))