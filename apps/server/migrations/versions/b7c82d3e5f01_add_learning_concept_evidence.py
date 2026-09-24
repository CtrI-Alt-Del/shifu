"""Persist versioned Concept evidence and unrounded progress.

Revision ID: b7c82d3e5f01
Revises: a6f71c2d4b90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b7c82d3e5f01'
down_revision: str | None = 'a6f71c2d4b90'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'learning_concept_observations',
        sa.Column('attempt_id', sa.String(length=26), nullable=False),
        sa.Column('concept_id', sa.String(length=26), nullable=False),
        sa.Column('skill_experience_id', sa.String(length=26), nullable=False),
        sa.Column('competency_id', sa.String(length=26), nullable=False),
        sa.Column('activity_id', sa.String(length=26), nullable=False),
        sa.Column('difficulty', sa.String(length=16), nullable=False),
        sa.Column('first_submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('question_scores', sa.JSON(), nullable=False),
        sa.Column('diagnostic', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ['attempt_id'], ['learning_activity_attempts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['skill_experience_id'],
            ['learning_skill_experiences.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('attempt_id', 'concept_id'),
    )
    op.create_index(
        'ix_learning_concept_observation_experience_concept_completed',
        'learning_concept_observations',
        ['skill_experience_id', 'concept_id', 'completed_at'],
    )
    op.create_table(
        'learning_concept_states',
        sa.Column('skill_experience_id', sa.String(length=26), nullable=False),
        sa.Column('concept_id', sa.String(length=26), nullable=False),
        sa.Column('competency_id', sa.String(length=26), nullable=False),
        sa.Column(
            'initial_progress', sa.Numeric(precision=20, scale=12), nullable=True
        ),
        sa.Column(
            'current_progress', sa.Numeric(precision=20, scale=12), nullable=True
        ),
        sa.Column('observed_difficulties', sa.JSON(), nullable=False),
        sa.Column('distinct_activity_ids', sa.JSON(), nullable=False),
        sa.Column('hard_confirmation', sa.Boolean(), nullable=False),
        sa.Column('evidence_verification', sa.Boolean(), nullable=False),
        sa.Column('inconclusive_activity_ids', sa.JSON(), nullable=False),
        sa.Column('current_contributions', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['skill_experience_id'],
            ['learning_skill_experiences.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('skill_experience_id', 'concept_id'),
        sa.CheckConstraint(
            'initial_progress IS NULL OR (initial_progress >= 0 AND initial_progress <= 100)',
            name='ck_learning_concept_state_initial_progress',
        ),
        sa.CheckConstraint(
            'current_progress IS NULL OR (current_progress >= 0 AND current_progress <= 100)',
            name='ck_learning_concept_state_current_progress',
        ),
    )
    op.create_index(
        'ix_learning_concept_state_experience_competency',
        'learning_concept_states',
        ['skill_experience_id', 'competency_id'],
    )
    op.alter_column(
        'learning_competency_progresses',
        'initial_progress',
        existing_type=sa.Numeric(precision=5, scale=2),
        type_=sa.Numeric(precision=20, scale=12),
        existing_nullable=True,
    )
    op.alter_column(
        'learning_competency_progresses',
        'current_progress',
        existing_type=sa.Numeric(precision=5, scale=2),
        type_=sa.Numeric(precision=20, scale=12),
        existing_nullable=True,
    )
    op.add_column(
        'learning_competency_progresses',
        sa.Column('verification_cause', sa.String(length=32), nullable=True),
    )
    op.add_column(
        'learning_competency_progresses',
        sa.Column('verification_concept_id', sa.String(length=26), nullable=True),
    )
    op.add_column(
        'learning_competency_progresses',
        sa.Column(
            'coverage_complete',
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('learning_competency_progresses', 'coverage_complete')
    op.drop_column('learning_competency_progresses', 'verification_concept_id')
    op.drop_column('learning_competency_progresses', 'verification_cause')
    op.alter_column(
        'learning_competency_progresses',
        'current_progress',
        existing_type=sa.Numeric(precision=20, scale=12),
        type_=sa.Numeric(precision=5, scale=2),
        existing_nullable=True,
    )
    op.alter_column(
        'learning_competency_progresses',
        'initial_progress',
        existing_type=sa.Numeric(precision=20, scale=12),
        type_=sa.Numeric(precision=5, scale=2),
        existing_nullable=True,
    )
    op.drop_index(
        'ix_learning_concept_state_experience_competency',
        table_name='learning_concept_states',
    )
    op.drop_table('learning_concept_states')
    op.drop_index(
        'ix_learning_concept_observation_experience_concept_completed',
        table_name='learning_concept_observations',
    )
    op.drop_table('learning_concept_observations')
