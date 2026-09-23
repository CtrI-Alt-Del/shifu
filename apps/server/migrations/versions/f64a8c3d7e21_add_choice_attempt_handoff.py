"""Add durable Learning choice attempt handoff and result state.

Revision ID: f64a8c3d7e21
Revises: e1a2b3c4d5e6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'f64a8c3d7e21'
down_revision: str | None = 'e1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'learning_activity_attempts',
        sa.Column('submission_key', sa.String(length=36), nullable=True),
    )
    op.add_column(
        'learning_activity_attempts',
        sa.Column('grading_snapshot', sa.JSON(), nullable=True),
    )
    op.add_column(
        'learning_activity_evaluations',
        sa.Column('run_id', sa.String(length=26), nullable=True),
    )
    op.add_column(
        'learning_activity_evaluations',
        sa.Column('progress_before', sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        'learning_activity_evaluations',
        sa.Column('progress_after', sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        'learning_activity_evaluations',
        sa.Column('status_before', sa.String(length=40), nullable=True),
    )
    op.add_column(
        'learning_activity_evaluations',
        sa.Column('status_after', sa.String(length=40), nullable=True),
    )
    op.execute(
        sa.text(
            'UPDATE learning_activity_evaluations '
            "SET status = 'failed', failure_code = 'archived_unscorable_legacy_attempt' "
            "WHERE status = 'pending' AND attempt_id IN ("
            'SELECT id FROM learning_activity_attempts WHERE grading_snapshot IS NULL)'
        )
    )
    op.create_index(
        'uq_learning_attempt_experience_submission_key',
        'learning_activity_attempts',
        ['skill_experience_id', 'submission_key'],
        unique=True,
        postgresql_where=sa.text('submission_key IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_learning_attempt_experience_submission_key',
        table_name='learning_activity_attempts',
    )
    op.drop_column('learning_activity_evaluations', 'status_after')
    op.drop_column('learning_activity_evaluations', 'status_before')
    op.drop_column('learning_activity_evaluations', 'progress_after')
    op.drop_column('learning_activity_evaluations', 'progress_before')
    op.drop_column('learning_activity_evaluations', 'run_id')
    op.drop_column('learning_activity_attempts', 'grading_snapshot')
    op.drop_column('learning_activity_attempts', 'submission_key')
