"""Extend companies table and add company_applications.

Revision ID: 20260423_0009
Revises: 20260331_0008
Create Date: 2026-04-23 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260423_0009"
down_revision = "20260331_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend companies ──────────────────────────────────────────────────────
    op.add_column("companies", sa.Column(
        "company_type", sa.String(20), nullable=False, server_default="transport"
    ))
    op.add_column("companies", sa.Column(
        "parent_company_id", sa.String(20),
        sa.ForeignKey("companies.company_id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("companies", sa.Column("cuit", sa.String(11), nullable=True))
    op.add_column("companies", sa.Column("fiscal_type", sa.String(30), nullable=True))
    op.add_column("companies", sa.Column("mp_account_id", sa.String(100), nullable=True))

    op.create_index("ix_companies_parent", "companies", ["parent_company_id"])
    op.create_index("ix_companies_cuit", "companies", ["cuit"])

    # ── Create company_applications ───────────────────────────────────────────
    op.create_table(
        "company_applications",
        sa.Column("application_id", sa.String(36), primary_key=True),
        sa.Column("company_type", sa.String(20), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("fiscal_type", sa.String(30), nullable=True),
        sa.Column("afip_data", JSONB, nullable=True),
        sa.Column("fiscal_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("fiscal_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mp_account_id", sa.String(100), nullable=True),
        sa.Column("mp_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mp_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "parent_company_id", sa.String(20),
            sa.ForeignKey("companies.company_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(100), nullable=False),
        sa.Column("documents", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column(
            "reviewed_by", sa.String(36),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_company_applications_status", "company_applications", ["status"])
    op.create_index("ix_company_applications_cuit", "company_applications", ["cuit"])
    op.create_index(
        "ix_company_applications_contact_email", "company_applications", ["contact_email"]
    )


def downgrade() -> None:
    op.drop_index("ix_company_applications_contact_email", table_name="company_applications")
    op.drop_index("ix_company_applications_cuit", table_name="company_applications")
    op.drop_index("ix_company_applications_status", table_name="company_applications")
    op.drop_table("company_applications")

    op.drop_index("ix_companies_cuit", table_name="companies")
    op.drop_index("ix_companies_parent", table_name="companies")
    op.drop_column("companies", "mp_account_id")
    op.drop_column("companies", "fiscal_type")
    op.drop_column("companies", "cuit")
    op.drop_column("companies", "parent_company_id")
    op.drop_column("companies", "company_type")
