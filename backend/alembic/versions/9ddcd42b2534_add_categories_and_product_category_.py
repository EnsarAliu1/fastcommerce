"""add categories and product category relationship

Revision ID: 9ddcd42b2534
Revises: f8e7276a3b65
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9ddcd42b2534"
down_revision: Union[str, Sequence[str], None] = "f8e7276a3b65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    op.create_index(
        op.f("ix_categories_id"),
        "categories",
        ["id"],
        unique=False,
    )

    # 2. Add category_id temporarily allowing NULL
    op.add_column(
        "products",
        sa.Column(
            "category_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # 3. Create fallback category for existing products
    op.execute(
        """
        INSERT INTO categories (name, slug)
        VALUES ('Uncategorized', 'uncategorized')
        """
    )

    # 4. Assign existing products to that category
    op.execute(
        """
        UPDATE products
        SET category_id = (
            SELECT id
            FROM categories
            WHERE slug = 'uncategorized'
        )
        WHERE category_id IS NULL
        """
    )

    # 5. Now category_id can safely become NOT NULL
    op.alter_column(
        "products",
        "category_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 6. Add foreign key
    op.create_foreign_key(
        "fk_products_category_id_categories",
        "products",
        "categories",
        ["category_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_category_id_categories",
        "products",
        type_="foreignkey",
    )

    op.drop_column(
        "products",
        "category_id",
    )

    op.drop_index(
        op.f("ix_categories_id"),
        table_name="categories",
    )

    op.drop_table(
        "categories",
    )
