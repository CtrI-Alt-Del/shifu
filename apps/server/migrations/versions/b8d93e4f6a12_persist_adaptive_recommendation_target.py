"""Keep the prior adaptive Concept target for deterministic continuity.

Revision ID: b8d93e4f6a12
Revises: b7c82d3e5f01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b8d93e4f6a12'
down_revision: str | None = 'b7c82d3e5f01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'learning_skill_experiences',
        sa.Column('recommended_concept_id', sa.String(length=26), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('learning_skill_experiences', 'recommended_concept_id')
