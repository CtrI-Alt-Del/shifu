"""Persist Learning rubric decisions until evaluation completion.

Revision ID: a10cf42957b3
Revises: b6f1d6a0c49e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a10cf42957b3'
down_revision: str | Sequence[str] | None = 'b6f1d6a0c49e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'learning_activity_evaluations',
        sa.Column(
            'rubric_decisions',
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('learning_activity_evaluations', 'rubric_decisions')
