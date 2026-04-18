"""CRM role model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_backend.db.base import Base


class CrmRole(Base):
    """Represent a functional role inside the CRM domain.

    Attributes:
        crm_role_id: Internal identifier.
        role_key: Stable key consumed by the frontend and permission checks.
        role_label: Human-readable label of the role.
        description: Human-readable description of the role responsibility.
        is_active: Whether the role can still be assigned.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "crm_roles"

    crm_role_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    role_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    role_label: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
