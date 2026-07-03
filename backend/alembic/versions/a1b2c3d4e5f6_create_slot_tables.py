"""create slot tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # stores テーブル
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("prefecture", sa.String(length=50), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stores_id"), "stores", ["id"], unique=False)

    # machines テーブル
    op.create_table(
        "machines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("machine_number", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=True),
        sa.Column("diff_medals", sa.Integer(), nullable=True),
        sa.Column("bonus_count", sa.Integer(), nullable=True),
        sa.Column("reg_count", sa.Integer(), nullable=True),
        sa.Column("big_count", sa.Integer(), nullable=True),
        sa.Column("at_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_machines_id"), "machines", ["id"], unique=False)
    op.create_index(
        op.f("ix_machines_store_date"),
        "machines",
        ["store_id", "date"],
        unique=False,
    )

    # predictions テーブル
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("machine_number", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("prediction_score", sa.Float(), nullable=False),
        sa.Column("predicted_setting", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)
    op.create_index(
        op.f("ix_predictions_store_date"),
        "predictions",
        ["store_id", "date"],
        unique=False,
    )

    # theoretical_values テーブル
    op.create_table(
        "theoretical_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("setting", sa.Integer(), nullable=False),
        sa.Column("reg_prob", sa.Float(), nullable=True),
        sa.Column("big_prob", sa.Float(), nullable=True),
        sa.Column("at_rate", sa.Float(), nullable=True),
        sa.Column("diff_rate_per_game", sa.Float(), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_name", "setting", name="uq_model_setting"),
    )
    op.create_index(
        op.f("ix_theoretical_values_id"), "theoretical_values", ["id"], unique=False
    )

    # scraping_logs テーブル
    op.create_table(
        "scraping_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scraped_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scraping_logs_id"), "scraping_logs", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scraping_logs_id"), table_name="scraping_logs")
    op.drop_table("scraping_logs")

    op.drop_index(op.f("ix_theoretical_values_id"), table_name="theoretical_values")
    op.drop_table("theoretical_values")

    op.drop_index(op.f("ix_predictions_store_date"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_id"), table_name="predictions")
    op.drop_table("predictions")

    op.drop_index(op.f("ix_machines_store_date"), table_name="machines")
    op.drop_index(op.f("ix_machines_id"), table_name="machines")
    op.drop_table("machines")

    op.drop_index(op.f("ix_stores_id"), table_name="stores")
    op.drop_table("stores")
