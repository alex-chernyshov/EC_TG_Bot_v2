"""add dtek_schedules

Revision ID: a1c3d5e7f901
Revises: 554dc3bb3721
Create Date: 2026-11-04 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1c3d5e7f901"
down_revision: Union[str, None] = "554dc3bb3721"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dtek_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_code", sa.String(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("hours", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("site_updated", sa.String(), nullable=False),
        sa.Column("date_fetched", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_code", "day"),
    )
    op.create_index(op.f("ix_dtek_schedules_group_code"), "dtek_schedules", ["group_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dtek_schedules_group_code"), table_name="dtek_schedules")
    op.drop_table("dtek_schedules")
