"""add brands and product brand relationship

Revision ID: b968e1b7d7ab
Revises: 9ddcd42b2534
Create Date: 2026-09-23 17:12:45.898034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b968e1b7d7ab'
down_revision: Union[str, Sequence[str], None] = '9ddcd42b2534'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "slug",
            name="uq_brands_slug"
        ),
    )

    op.create_index(
        op.f("ix_brands_id"),
        "brands",
        ["id"],
        unique=False,
    )

    # Temporarily nullable because products already exist
    op.add_column(
        "products",
        sa.Column(
            "brand_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Fallback brand for existing products
    op.execute(
        """
        INSERT INTO brands (name, slug)
        VALUES ('Unbranded', 'unbranded')
        """
    )

    # Assign existing products to fallback brand
    op.execute(
        """
        UPDATE products
        SET brand_id = (
            SELECT id
            FROM brands
            WHERE slug = 'unbranded'
        )
        WHERE brand_id IS NULL
        """
    )

    # Now safe to enforce NOT NULL
    op.alter_column(
        "products",
        "brand_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_products_brand_id_brands",
        "products",
        "brands",
        ["brand_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_brand_id_brands",
        "products",
        type_="foreignkey",
    )

    op.drop_column(
        "products",
        "brand_id",
    )

    op.drop_index(
        op.f("ix_brands_id"),
        table_name="brands",
    )

    op.drop_table(
        "brands",
    )
