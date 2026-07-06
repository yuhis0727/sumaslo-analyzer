"""add unique constraint to machines

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_machines_date",
        "machines",
        ["date"],
        unique=False,
    )
    op.create_index(
        "ix_machines_machine_number",
        "machines",
        ["machine_number"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_machines_store_num_date",
        "machines",
        ["store_id", "machine_number", "date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_machines_store_num_date", "machines", type_="unique")
    op.drop_index("ix_machines_machine_number", table_name="machines")
    op.drop_index("ix_machines_date", table_name="machines")
