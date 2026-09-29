"""Add an optional, fixed initial diagnostic sequence to Curriculum Skills.

Revision ID: ba1d8c9e2f34
Revises: cddf4217a4b7
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'ba1d8c9e2f34'
down_revision: str | None = 'cddf4217a4b7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'curriculum_skills',
        sa.Column(
            'initial_diagnostic_activity_ids',
            sa.JSON(),
            server_default='[]',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('curriculum_skills', 'initial_diagnostic_activity_ids')
