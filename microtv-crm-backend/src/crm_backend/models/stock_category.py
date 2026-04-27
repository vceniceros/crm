"""Modelo ORM de categorías de depósito."""

from __future__ import annotations

from datetime import datetime
import re
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class StockCategory(Base):
    """Representa una categoría operativa para productos de depósito.

    Attributes:
        category_id: Identificador UUID del schema v4.
        name: Nombre visible de la categoría.
        is_active: Indica si la categoría puede usarse en nuevas altas.
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
        products: Productos vinculados a la categoría.
    """

    __tablename__ = "inventory_categories"

    category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    category_name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    parent_category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    products: Mapped[list[StockProduct]] = relationship("StockProduct", back_populates="category", lazy="selectin")

    @property
    def stock_category_id(self) -> str:
        return self.category_id

    @property
    def name(self) -> str:
        return self.category_name

    @property
    def code(self) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", self.category_name.lower()).strip("-")
        return normalized or self.category_id