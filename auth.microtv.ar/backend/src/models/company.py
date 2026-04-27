from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Company classification and hierarchy
    company_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="transport", server_default="transport"
    )
    # Values: 'transport' | 'transport_sub' | 'merchant_solo' | 'merchant_company'

    parent_company_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("companies.company_id", ondelete="SET NULL"), nullable=True
    )

    # Fiscal identity (Argentina)
    cuit: Mapped[str | None] = mapped_column(String(11), nullable=True)
    fiscal_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Values: 'monotributo' | 'responsable_inscripto' | 'sociedad' | 'exento'

    # MercadoPago Connect
    mp_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_companies_status", "status"),
        Index("ix_companies_parent", "parent_company_id"),
        Index("ix_companies_cuit", "cuit"),
    )
