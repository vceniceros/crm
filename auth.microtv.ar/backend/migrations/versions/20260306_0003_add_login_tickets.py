"""Add login tickets.

Revision ID: 20260306_0003
Revises: 20260306_0002
Create Date: 2026-03-06 00:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260306_0003"
down_revision = "20260306_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_tickets",
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("ticket_id"),
    )
    op.create_index(op.f("ix_login_tickets_expires_at"), "login_tickets", ["expires_at"], unique=False)
    op.create_index(op.f("ix_login_tickets_user_id"), "login_tickets", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_login_tickets_user_id"), table_name="login_tickets")
    op.drop_index(op.f("ix_login_tickets_expires_at"), table_name="login_tickets")
    op.drop_table("login_tickets")
