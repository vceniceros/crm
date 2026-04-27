"""Seed CRM operational roles.

Revision ID: 20260425_0010
Revises: 20260423_0009
Create Date: 2026-04-25 10:00:00
"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260425_0010"
down_revision = "20260423_0009"
branch_labels = None
depends_on = None

_ROLES = [
    "admin",
    "ejecutivo",
    "tecnico_campo",
    "operador_deposito",
]


def upgrade() -> None:
    for role_name in _ROLES:
        op.execute(
            sa.text(
                "INSERT INTO roles (role_id, role_name) VALUES (:role_id, :role_name) "
                "ON CONFLICT (role_name) DO NOTHING"
            ).bindparams(role_id=str(uuid4()), role_name=role_name)
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM roles WHERE role_name = ANY(:names)").bindparams(names=_ROLES))
