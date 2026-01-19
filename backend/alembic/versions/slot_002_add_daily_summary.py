"""add detail tables for slot analysis

Revision ID: slot_002
Revises: slot_001
Create Date: 2025-01-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "slot_002"
down_revision: Union[str, None] = "slot_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # slot_machines テーブルに確率カラムを追加
    op.add_column(
        "slot_machines",
        sa.Column("bb_probability", sa.String(50), nullable=True),
    )
    op.add_column(
        "slot_machines",
        sa.Column("rb_probability", sa.String(50), nullable=True),
    )
    op.add_column(
        "slot_machines",
        sa.Column("combined_probability", sa.String(50), nullable=True),
    )

    # data_date カラムの型を DateTime から Date に変更
    op.alter_column(
        "slot_machines",
        "data_date",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=False,
    )

    # slot_machines にユニーク制約を追加
    op.create_unique_constraint(
        "uq_machine_date",
        "slot_machines",
        ["store_id", "machine_number", "data_date"],
    )

    # daily_store_summaries テーブルを作成
    op.create_table(
        "daily_store_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("data_date", sa.Date(), nullable=False),
        sa.Column("total_machines", sa.Integer(), nullable=False),
        sa.Column("positive_machines", sa.Integer(), nullable=True),
        sa.Column("negative_machines", sa.Integer(), nullable=True),
        sa.Column("total_difference", sa.Integer(), nullable=True),
        sa.Column("average_difference", sa.Float(), nullable=True),
        sa.Column("average_game_count", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
        ),
        sa.UniqueConstraint("store_id", "data_date", name="uq_store_date_summary"),
    )
    op.create_index(
        op.f("ix_daily_store_summaries_id"),
        "daily_store_summaries",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_store_summaries_store_date",
        "daily_store_summaries",
        ["store_id", "data_date"],
        unique=False,
    )

    # slot_models テーブル（機種マスター）
    op.create_table(
        "slot_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("maker", sa.String(255), nullable=True),
        sa.Column("type", sa.String(50), nullable=True),
        sa.Column("max_payout", sa.Integer(), nullable=True),
        sa.Column("setting_1_payout", sa.Float(), nullable=True),
        sa.Column("setting_2_payout", sa.Float(), nullable=True),
        sa.Column("setting_5_payout", sa.Float(), nullable=True),
        sa.Column("setting_6_payout", sa.Float(), nullable=True),
        sa.Column("setting_hints", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_slot_model_name"),
    )
    op.create_index(
        op.f("ix_slot_models_id"), "slot_models", ["id"], unique=False
    )

    # daily_model_summaries テーブル（機種別日次サマリー）
    op.create_table(
        "daily_model_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("data_date", sa.Date(), nullable=False),
        sa.Column("machine_count", sa.Integer(), nullable=False),
        sa.Column("total_game_count", sa.Integer(), nullable=True),
        sa.Column("average_game_count", sa.Float(), nullable=True),
        sa.Column("total_difference", sa.Integer(), nullable=True),
        sa.Column("average_difference", sa.Float(), nullable=True),
        sa.Column("positive_count", sa.Integer(), nullable=True),
        sa.Column("max_difference", sa.Integer(), nullable=True),
        sa.Column("min_difference", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["slot_models.id"]),
        sa.UniqueConstraint(
            "store_id", "model_id", "data_date", name="uq_store_model_date"
        ),
    )
    op.create_index(
        op.f("ix_daily_model_summaries_id"),
        "daily_model_summaries",
        ["id"],
        unique=False,
    )

    # machine_position_histories テーブル（台番号履歴）
    op.create_table(
        "machine_position_histories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("machine_number", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("data_count", sa.Integer(), nullable=False),
        sa.Column("total_difference", sa.Integer(), nullable=True),
        sa.Column("average_difference", sa.Float(), nullable=True),
        sa.Column("positive_days", sa.Integer(), nullable=True),
        sa.Column("negative_days", sa.Integer(), nullable=True),
        sa.Column("max_difference", sa.Integer(), nullable=True),
        sa.Column("min_difference", sa.Integer(), nullable=True),
        sa.Column("high_setting_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.UniqueConstraint(
            "store_id",
            "machine_number",
            "period_start",
            "period_end",
            name="uq_position_period",
        ),
    )
    op.create_index(
        op.f("ix_machine_position_histories_id"),
        "machine_position_histories",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    # machine_position_histories テーブルを削除
    op.drop_index(
        op.f("ix_machine_position_histories_id"),
        table_name="machine_position_histories",
    )
    op.drop_table("machine_position_histories")

    # daily_model_summaries テーブルを削除
    op.drop_index(
        op.f("ix_daily_model_summaries_id"),
        table_name="daily_model_summaries",
    )
    op.drop_table("daily_model_summaries")

    # slot_models テーブルを削除
    op.drop_index(op.f("ix_slot_models_id"), table_name="slot_models")
    op.drop_table("slot_models")

    # daily_store_summaries テーブルを削除
    op.drop_index(
        "ix_daily_store_summaries_store_date",
        table_name="daily_store_summaries",
    )
    op.drop_index(
        op.f("ix_daily_store_summaries_id"),
        table_name="daily_store_summaries",
    )
    op.drop_table("daily_store_summaries")

    # slot_machines からユニーク制約を削除
    op.drop_constraint("uq_machine_date", "slot_machines", type_="unique")

    # data_date カラムの型を Date から DateTime に戻す
    op.alter_column(
        "slot_machines",
        "data_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=False,
    )

    # slot_machines から確率カラムを削除
    op.drop_column("slot_machines", "combined_probability")
    op.drop_column("slot_machines", "rb_probability")
    op.drop_column("slot_machines", "bb_probability")
