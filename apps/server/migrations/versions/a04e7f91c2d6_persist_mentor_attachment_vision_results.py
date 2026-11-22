"""Persist recoverable mentor attachment vision results.

Revision ID: a04e7f91c2d6
Revises: b6f1d6a0c49e
Create Date: 2026-11-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'a04e7f91c2d6'
down_revision: str | Sequence[str] | None = 'b6f1d6a0c49e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'intelligence_mentor_attachments',
        sa.Column(
            'vision_results',
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('intelligence_mentor_attachments', 'vision_results')
