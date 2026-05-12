"""Permission models for role defaults and user overrides."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_backend.db.base import Base


class RolePermission(Base):
    """Permission defaults per role key."""

    __tablename__ = "crm_role_permissions"
    __table_args__ = (UniqueConstraint("role_key", "permission_code", name="uq_crm_role_permission"),)

    role_permission_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    role_key: Mapped[str] = mapped_column(String(50), index=True)
    permission_code: Mapped[str] = mapped_column(String(100))
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPermission(Base):
    """Per-user permission overrides."""

    __tablename__ = "crm_user_permissions"
    __table_args__ = (UniqueConstraint("crm_user_id", "permission_code", name="uq_crm_user_permission"),)

    user_permission_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id", ondelete="CASCADE"), index=True)
    permission_code: Mapped[str] = mapped_column(String(100))
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    granted_by_crm_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("crm_users.crm_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
