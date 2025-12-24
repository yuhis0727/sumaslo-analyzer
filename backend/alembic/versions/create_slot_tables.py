"""create slot tables

Revision ID: slot_001
Revises:
Create Date: 2025-12-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'slot_001'
down_revision: Union[str, None] = '04e949445662'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # stores テーブル
    op.create_table(
        'stores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('area', sa.String(255), nullable=True),
        sa.Column('anaslo_url', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stores_id'), 'stores', ['id'], unique=False)

    # slot_machines テーブル
    op.create_table(
        'slot_machines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('machine_number', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('game_count', sa.Integer(), nullable=True),
        sa.Column('big_bonus', sa.Integer(), nullable=True),
        sa.Column('regular_bonus', sa.Integer(), nullable=True),
        sa.Column('art_count', sa.Integer(), nullable=True),
        sa.Column('total_difference', sa.Integer(), nullable=True),
        sa.Column('data_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], )
    )
    op.create_index(op.f('ix_slot_machines_id'), 'slot_machines', ['id'], unique=False)

    # predictions テーブル
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('prediction_date', sa.DateTime(), nullable=False),
        sa.Column('high_setting_probability', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('recommended_machines', sa.Text(), nullable=True),
        sa.Column('analysis_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], )
    )
    op.create_index(op.f('ix_predictions_id'), 'predictions', ['id'], unique=False)

    # scraping_logs テーブル
    op.create_table(
        'scraping_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('scraped_count', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], )
    )
    op.create_index(op.f('ix_scraping_logs_id'), 'scraping_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_scraping_logs_id'), table_name='scraping_logs')
    op.drop_table('scraping_logs')
    op.drop_index(op.f('ix_predictions_id'), table_name='predictions')
    op.drop_table('predictions')
    op.drop_index(op.f('ix_slot_machines_id'), table_name='slot_machines')
    op.drop_table('slot_machines')
    op.drop_index(op.f('ix_stores_id'), table_name='stores')
    op.drop_table('stores')
