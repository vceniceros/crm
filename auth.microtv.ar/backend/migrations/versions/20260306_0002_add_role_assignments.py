"""Add role assignments.

Revision ID: 20260306_0002
Revises: 20260306_0001
Create Date: 2026-03-06 00:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260306_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_assignments",
        sa.Column("assignment_id", sa.String(length=36), nullable=False),
        sa.Column("membership_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.membership_id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"]),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_index(op.f("ix_role_assignments_membership_id"), "role_assignments", ["membership_id"], unique=False)
    op.create_index(op.f("ix_role_assignments_role_id"), "role_assignments", ["role_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_role_assignments_role_id"), table_name="role_assignments")
    op.drop_index(op.f("ix_role_assignments_membership_id"), table_name="role_assignments")
    op.drop_table("role_assignments")
