"""Add companies table and user_type column.

Revision ID: 20260308_0005
Revises: 20260308_0004
Create Date: 2026-03-08 01:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260308_0005"
down_revision = "20260308_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("company_id", sa.String(length=20), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("company_id"),
    )
    op.create_index(op.f("ix_companies_status"), "companies", ["status"], unique=False)

    op.add_column(
        "users",
        sa.Column(
            "user_type",
            sa.String(length=30),
            nullable=False,
            server_default="customer",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "user_type")
    op.drop_index(op.f("ix_companies_status"), table_name="companies")
    op.drop_table("companies")
