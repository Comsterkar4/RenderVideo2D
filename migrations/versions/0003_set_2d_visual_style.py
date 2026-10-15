"""Set the fixed visual style to hand-drawn 2D animation.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TWO_D_VISUAL_STYLE = "hoạt hình 2D vẽ tay, màu phẳng, đường nét rõ, thân thiện với trẻ em"
THREE_D_VISUAL_STYLE = "hoạt hình 3D, màu sắc ấm áp, thân thiện với trẻ em"


def upgrade() -> None:
    projects = sa.table("projects", sa.column("visual_style", sa.String(length=500)))
    op.execute(projects.update().values(visual_style=TWO_D_VISUAL_STYLE))


def downgrade() -> None:
    projects = sa.table("projects", sa.column("visual_style", sa.String(length=500)))
    op.execute(projects.update().values(visual_style=THREE_D_VISUAL_STYLE))
