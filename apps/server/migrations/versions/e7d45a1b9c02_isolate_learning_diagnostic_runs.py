"""isolate_learning_diagnostic_runs

Revision ID: e7d45a1b9c02
Revises: c9e4f6a7b8c1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e7d45a1b9c02'
down_revision: str | None = 'c9e4f6a7b8c1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'learning_skill_experiences',
        sa.Column('diagnostic_run_id', sa.String(length=36), nullable=True),
    )
    op.add_column(
        'learning_activity_attempts',
        sa.Column('diagnostic_run_id', sa.String(length=36), nullable=True),
    )
    op.create_index(
        'ix_learning_attempt_experience_diagnostic_run_kind',
        'learning_activity_attempts',
        ['skill_experience_id', 'diagnostic_run_id', 'kind'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_learning_attempt_experience_diagnostic_run_kind',
        table_name='learning_activity_attempts',
    )
    op.drop_column('learning_activity_attempts', 'diagnostic_run_id')
    op.drop_column('learning_skill_experiences', 'diagnostic_run_id')
