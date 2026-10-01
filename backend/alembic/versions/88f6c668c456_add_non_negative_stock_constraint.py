"""add non negative stock constraint

Revision ID: 88f6c668c456
Revises: ad2844054f97
Create Date: 2026-10-01 13:14:51.058291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88f6c668c456'
down_revision: Union[str, Sequence[str], None] = 'ad2844054f97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_product_variants_stock_quantity_non_negative",
        "product_variants",
        "stock_quantity >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_product_variants_stock_quantity_non_negative",
        "product_variants",
        type_="check",
    )
