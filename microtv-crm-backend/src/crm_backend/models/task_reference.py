"""Minimal reference models required by task foreign keys."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from crm_backend.db.base import Base


class Client(Base):
    """Client reference table used by task records."""

    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    business_name: Mapped[str] = mapped_column(String(255))
    tax_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Location(Base):
    """Location reference table used by task records."""

    __tablename__ = "locations"

    location_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    latitude: Mapped[float] = mapped_column(Numeric(10, 8))
    longitude: Mapped[float] = mapped_column(Numeric(11, 8))
    address_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClientLocation(Base):
    """Primary client-to-location association used by the CRM clients module."""

    __tablename__ = "client_locations"

    client_location_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    client_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("clients.client_id", ondelete="CASCADE"), index=True)
    location_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), ForeignKey("locations.location_id", ondelete="CASCADE"), index=True)
    location_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())