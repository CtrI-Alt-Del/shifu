"""Add private, immutable Learning ordering passage state.

Revision ID: 61de5a9b2c84
Revises: ad56e779665a
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '61de5a9b2c84'
down_revision: str | None = 'ad56e779665a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'learning_ordering_passages',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('skill_experience_id', sa.String(length=26), nullable=False),
        sa.Column('activity_id', sa.String(length=26), nullable=False),
        sa.Column('passage_key', sa.String(length=36), nullable=False),
        sa.Column('activity_revision', sa.String(length=128), nullable=False),
        sa.Column('grading_snapshot', sa.JSON(), nullable=False),
        sa.Column('verified_orderings', sa.JSON(), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'consumed')",
            name='ck_learning_ordering_passage_status',
        ),
        sa.ForeignKeyConstraint(
            ['skill_experience_id'],
            ['learning_skill_experiences.id'],
            name='fk_learning_ordering_passage_experience',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_learning_ordering_passage_experience_activity_key',
        'learning_ordering_passages',
        ['skill_experience_id', 'activity_id', 'passage_key'],
        unique=True,
    )
    op.create_index(
        'uq_learning_ordering_passage_active_experience_activity',
        'learning_ordering_passages',
        ['skill_experience_id', 'activity_id'],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_learning_ordering_passage_active_experience_activity',
        table_name='learning_ordering_passages',
    )
    op.drop_index(
        'uq_learning_ordering_passage_experience_activity_key',
        table_name='learning_ordering_passages',
    )
    op.drop_table('learning_ordering_passages')
