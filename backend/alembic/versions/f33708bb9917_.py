"""empty message

Revision ID: f33708bb9917
Revises: 46bd37a7005e
Create Date: 2024-11-04 07:24:38.834083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f33708bb9917'
down_revision: Union[str, None] = '46bd37a7005e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('orders', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('orders', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.execute("UPDATE orders SET created_at = NOW(), updated_at = NOW() WHERE created_at IS NULL OR updated_at IS NULL")

    # その後にデフォルトを削除する
    op.alter_column('orders', 'created_at', server_default=None)
    op.alter_column('orders', 'updated_at', server_default=None)

def downgrade() -> None:
    op.drop_column('orders', 'updated_at')
    op.drop_column('orders', 'created_at')
