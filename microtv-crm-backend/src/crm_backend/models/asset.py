"""Asset aggregate models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base

if TYPE_CHECKING:
    from crm_backend.models.asset_category import AssetCategory, AssetCategoryField
    from crm_backend.models.crm_user import CrmUser
    from crm_backend.models.task_reference import Client


class Asset(Base):
    """Physical asset owned by a client."""

    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    category_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("asset_categories.asset_category_id"), index=True)
    client_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("clients.client_id"), index=True)
    parent_asset_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("assets.asset_id"), nullable=True, index=True)
    asset_name: Mapped[str] = mapped_column(String(255), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped["AssetCategory"] = relationship("AssetCategory", lazy="joined")
    client: Mapped["Client"] = relationship("Client", lazy="joined")
    parent_asset: Mapped["Asset | None"] = relationship("Asset", remote_side=[asset_id], lazy="joined")
    created_by_user: Mapped["CrmUser"] = relationship("CrmUser", foreign_keys=[created_by_crm_user_id], lazy="joined")
    field_values: Mapped[list["AssetFieldValue"]] = relationship(
        "AssetFieldValue",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def category_name(self) -> str:
        return self.category.category_name

    @property
    def client_name(self) -> str:
        return self.client.business_name

    @property
    def parent_asset_name(self) -> str | None:
        return self.parent_asset.asset_name if self.parent_asset is not None else None


class AssetFieldValue(Base):
    """Persisted value for one configured asset category field."""

    __tablename__ = "asset_field_values"
    __table_args__ = (
        UniqueConstraint("asset_id", "field_id", name="uq_asset_field_values_asset_field"),
    )

    field_value_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    asset_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("assets.asset_id"), index=True)
    field_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("asset_category_fields.field_id"), index=True)
    raw_value: Mapped[str] = mapped_column(Text, default="", server_default="")

    asset: Mapped[Asset] = relationship("Asset", back_populates="field_values")
    field: Mapped["AssetCategoryField"] = relationship("AssetCategoryField", lazy="joined")

    @property
    def field_name(self) -> str:
        return self.field.field_name

    @property
    def field_type(self) -> str:
        return self.field.field_type
