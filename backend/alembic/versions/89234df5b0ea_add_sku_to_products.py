"""add sku to products

Revision ID: 89234df5b0ea
Revises: 1f3bb4891227
Create Date: 2026-09-17 17:52:12.799069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89234df5b0ea'
down_revision: Union[str, Sequence[str], None] = '1f3bb4891227'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'products',
        sa.Column(
            'sku',
            sa.String(length=100),
            nullable=False
        )
    )

    op.create_unique_constraint(
        'uq_products_sku',
        'products',
        ['sku']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_products_sku',
        'products',
        type_='unique'
    )

    op.drop_column(
        'products',
        'sku'
    )
