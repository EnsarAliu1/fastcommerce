"""remove product in_stock

Revision ID: ad2844054f97
Revises: bb9134da863f
Create Date: 2026-09-28 19:43:13.109380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad2844054f97'
down_revision: Union[str, Sequence[str], None] = 'bb9134da863f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.drop_column(
        "products",
        "in_stock"
    )


def downgrade() -> None:
    """Downgrade schema."""

    # 1. Add column temporarily nullable
    op.add_column(
        "products",
        sa.Column(
            "in_stock",
            sa.Boolean(),
            nullable=True
        )
    )

    # 2. Recalculate stock status from variants
    op.execute(
        """
        UPDATE products
        SET in_stock = EXISTS (
            SELECT 1
            FROM product_variants
            WHERE product_variants.product_id = products.id
              AND product_variants.stock_quantity > 0
        )
        """
    )

    # 3. Make it NOT NULL again
    op.alter_column(
        "products",
        "in_stock",
        existing_type=sa.Boolean(),
        nullable=False
    )
