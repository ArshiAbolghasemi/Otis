"""replace model_type with product_id

Revision ID: a1c4f7d92b03
Revises: fc8261c07516
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c4f7d92b03"
down_revision: str | None = "fc8261c07516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The free-text model type is replaced by the AI Farm product id (1-11).
    # Existing rows predate the catalogue, so they fall back to product 1.
    op.add_column(
        "submissions",
        sa.Column("product_id", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("submissions", "product_id", server_default=None)
    op.drop_column("submissions", "model_type")


def downgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("model_type", sa.String(length=128), nullable=False, server_default=""),
    )
    op.alter_column("submissions", "model_type", server_default=None)
    op.drop_column("submissions", "product_id")
