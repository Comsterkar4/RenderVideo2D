"""Add sound effects to scenes.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.add_column(
            sa.Column("sound_effects", sa.JSON(), nullable=False, server_default="[]")
        )



def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.drop_column("sound_effects")
