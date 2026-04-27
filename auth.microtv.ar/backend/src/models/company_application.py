from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class CompanyApplication(Base):
    __tablename__ = "company_applications"

    application_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # What kind of company is applying
    company_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Values: 'transport_sub' | 'merchant_solo' | 'merchant_company'

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Fiscal identity (Argentina)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False)
    fiscal_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Values: 'monotributo' | 'responsable_inscripto' | 'sociedad' | 'exento'
    afip_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fiscal_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fiscal_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # MercadoPago Connect
    mp_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mp_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mp_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # For transport_sub: link to the known parent transport company
    parent_company_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True
    )

    # Applicant contact (becomes the company manager on approval)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional supporting documents (URLs), mainly for merchant_company
    documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # State machine
    # draft → submitted → fiscal_verified → mp_verified → under_review → approved | rejected
    # rejected applications can be corrected and re-submitted (back to draft)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review metadata
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_company_applications_status", "status"),
        Index("ix_company_applications_cuit", "cuit"),
        Index("ix_company_applications_contact_email", "contact_email"),
    )
