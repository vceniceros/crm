"""Asset category models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.crm_user import CrmUser


class AssetCategory(Base):
    """Dynamic asset category configured by CRM admins."""

    __tablename__ = "asset_categories"

    asset_category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    category_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_crm_user_id], lazy="joined")
    fields: Mapped[list["AssetCategoryField"]] = relationship(
        "AssetCategoryField",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="AssetCategoryField.order_index",
        lazy="selectin",
    )


class AssetCategoryField(Base):
    """Typed field definition for an asset category."""

    __tablename__ = "asset_category_fields"
    __table_args__ = (
        UniqueConstraint("category_id", "field_name", name="uq_asset_category_fields_category_name"),
    )

    field_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("asset_categories.asset_category_id"), index=True)
    field_name: Mapped[str] = mapped_column(String(120))
    field_type: Mapped[str] = mapped_column(String(30))
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    order_index: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[AssetCategory] = relationship("AssetCategory", back_populates="fields")
