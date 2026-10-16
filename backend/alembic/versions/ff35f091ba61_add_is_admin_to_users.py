"""add is_admin to users

Revision ID: ff35f091ba61
Revises: 3a4e16e201d4
Create Date: 2026-10-16 15:36:01.710912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff35f091ba61'
down_revision: Union[str, Sequence[str], None] = '3a4e16e201d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
