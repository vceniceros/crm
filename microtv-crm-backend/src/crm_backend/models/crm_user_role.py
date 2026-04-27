"""CRM user role assignment model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class CrmUserRole(Base):
    """Represent a local CRM role assignment for a CRM user.

    Attributes:
        crm_user_role_id: Internal assignment identifier.
        crm_user_id: Internal CRM user identifier.
        crm_role_id: Internal CRM role identifier.
        assigned_at: Creation timestamp.
        user: Assigned CRM user.
        role: Assigned CRM role.
    """

    __tablename__ = "crm_user_roles"
    __table_args__ = (UniqueConstraint("crm_user_id", "crm_role_id", name="uq_crm_user_role"),)

    crm_user_role_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), index=True)
    crm_role_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_roles.crm_role_id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assigned_by_crm_user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), ForeignKey("crm_users.crm_user_id"), nullable=True)

    user: Mapped[CrmUser] = relationship(
        "CrmUser",
        back_populates="assigned_roles",
        foreign_keys=[crm_user_id],
    )
    role: Mapped[CrmRole] = relationship("CrmRole", lazy="joined")
