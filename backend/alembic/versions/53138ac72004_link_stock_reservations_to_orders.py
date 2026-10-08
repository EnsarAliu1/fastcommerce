"""link stock reservations to orders

Revision ID: 53138ac72004
Revises: 75e9fe70d5e3
Create Date: 2026-10-08 20:04:39.768937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53138ac72004'
down_revision: Union[str, Sequence[str], None] = '75e9fe70d5e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stock_reservations",
        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=True
        )
    )

    op.create_index(
        op.f("ix_stock_reservations_order_id"),
        "stock_reservations",
        ["order_id"],
        unique=False
    )

    op.create_foreign_key(
        "fk_stock_reservations_order_id_orders",
        "stock_reservations",
        "orders",
        ["order_id"],
        ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_stock_reservations_order_id_orders",
        "stock_reservations",
        type_="foreignkey"
    )

    op.drop_index(
        op.f("ix_stock_reservations_order_id"),
        table_name="stock_reservations"
    )

    op.drop_column(
        "stock_reservations",
        "order_id"
    )
