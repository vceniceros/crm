"""Modelos ORM para importaciones seguras de stock."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class StockImportBatch(Base):
    """Lote de importacion de stock en dos pasos."""

    __tablename__ = "stock_import_batches"

    import_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    confirmed_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_import_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rows: Mapped[list["StockImportRow"]] = relationship(
        "StockImportRow",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="StockImportRow.row_number",
        lazy="selectin",
    )
    backup: Mapped["StockBackup | None"] = relationship("StockBackup", back_populates="batch", uselist=False, lazy="selectin")


class StockImportRow(Base):
    """Fila parseada y validada de una importacion."""

    __tablename__ = "stock_import_rows"

    import_row_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    import_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("stock_import_batches.import_id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    product_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    category_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_categories.category_id"), nullable=True)
    imported_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    old_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shelf_id: Mapped[str | None] = mapped_column(String(1), nullable=True)
    shelf_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_new_product: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    errors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    product_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id"), nullable=True)

    batch: Mapped[StockImportBatch] = relationship("StockImportBatch", back_populates="rows")


class StockBackup(Base):
    """Backup de inventario generado antes de confirmar una importacion."""

    __tablename__ = "stock_backups"

    backup_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    import_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("stock_import_batches.import_id"), unique=True, index=True)
    created_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    rolled_back_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped[StockImportBatch] = relationship("StockImportBatch", back_populates="backup")
    rows: Mapped[list["StockBackupRow"]] = relationship(
        "StockBackupRow",
        back_populates="backup",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StockBackupRow(Base):
    """Snapshot de un producto antes de una importacion."""

    __tablename__ = "stock_backup_rows"

    backup_row_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    backup_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("stock_backups.backup_id"), index=True)
    product_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_products.product_id"), index=True)
    product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("inventory_categories.category_id"), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shelf_id: Mapped[str | None] = mapped_column(String(1), nullable=True)
    shelf_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    backup: Mapped[StockBackup] = relationship("StockBackup", back_populates="rows")
