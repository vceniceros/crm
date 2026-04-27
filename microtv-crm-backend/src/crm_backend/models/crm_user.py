"""CRM user model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crm_backend.db.base import Base


class CrmUser(Base):
    """Represent the local CRM operational user profile.

    The CRM user stores only local operational data plus a snapshot of the
    authenticated auth context. Credentials and token lifecycle remain external.

    Attributes:
        crm_user_id: Internal CRM identifier.
        auth_user_id: External identity identifier from auth `sub`.
        email: Cached email from auth claims.
        display_name: Cached display name when available.
        last_auth_membership_id: Snapshot of the active auth membership id.
        last_auth_tenant_type: Snapshot of the active tenant type.
        last_auth_tenant_id: Snapshot of the active tenant id.
        last_auth_roles_json: Snapshot of external auth roles for the active membership.
        is_active_in_crm: Local CRM operational flag.
        cached_at: When identity cache fields were refreshed.
        last_auth_context_synced_at: When auth context snapshot was refreshed.
        phone: Optional contact phone.
        initials: Optional short initials.
        last_seen_in_crm_at: Last successful CRM activity timestamp.
        deleted_at: Soft-delete marker defined by schema v4.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        assigned_roles: Local CRM role assignments.
    """

    __tablename__ = "crm_users"

    crm_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    auth_user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_auth_membership_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_auth_tenant_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_auth_tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_auth_roles_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    initials: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active_in_crm: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_seen_in_crm_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_auth_context_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assigned_roles: Mapped[list[CrmUserRole]] = relationship(
        "CrmUserRole",
        back_populates="user",
        foreign_keys="CrmUserRole.crm_user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def sync_identity_snapshot(self, *, email: str | None, display_name: str | None, synced_at: datetime) -> None:
        """Refresh locally cached identity fields.

        Args:
            email: Email from external auth claims.
            display_name: Display name from external auth claims.
            synced_at: Timestamp used for cache metadata.
        """

        self.email = email
        if display_name:
            self.display_name = display_name
        self.cached_at = synced_at

    def sync_auth_context(
        self,
        *,
        membership_id: str | None,
        tenant_type: str | None,
        tenant_id: str | None,
        roles: list[str],
        synced_at: datetime,
    ) -> None:
        """Refresh the snapshot of the active auth context.

        Args:
            membership_id: Auth membership identifier.
            tenant_type: Auth tenant type.
            tenant_id: Auth tenant identifier.
            roles: External auth roles in the active membership.
            synced_at: Timestamp used for snapshot metadata.
        """

        self.last_auth_membership_id = membership_id
        self.last_auth_tenant_type = tenant_type
        self.last_auth_tenant_id = tenant_id
        self.last_auth_roles_json = roles
        self.last_auth_context_synced_at = synced_at

    def register_successful_login(self, occurred_at: datetime) -> None:
        """Store the last successful login timestamp.

        Args:
            occurred_at: Timestamp of the successful login.
        """

        self.last_seen_in_crm_at = occurred_at
