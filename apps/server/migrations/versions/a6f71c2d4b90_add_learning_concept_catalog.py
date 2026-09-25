"""Add the versioned Learning Concept catalog without changing legacy experiences.

Revision ID: a6f71c2d4b90
Revises: f64a8c3d7e21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a6f71c2d4b90'
down_revision: str | None = 'f64a8c3d7e21'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'curriculum_concepts',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('competency_id', sa.String(length=26), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.String(length=4000), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('observation_criteria', sa.String(length=4000), nullable=False),
        sa.Column(
            'prerequisite_ids',
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['competency_id'], ['curriculum_competencies.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            'position >= 1', name='ck_curriculum_concept_position_positive'
        ),
        sa.UniqueConstraint(
            'competency_id',
            'position',
            name='uq_curriculum_concept_competency_position',
        ),
    )
    op.create_index(
        'ix_curriculum_concept_competency_position',
        'curriculum_concepts',
        ['competency_id', 'position'],
    )
    op.add_column(
        'curriculum_materials',
        sa.Column(
            'concept_ids', sa.JSON(), server_default=sa.text("'[]'"), nullable=False
        ),
    )
    op.add_column(
        'curriculum_activities',
        sa.Column(
            'required_concept_ids',
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.add_column(
        'learning_skill_experiences',
        sa.Column(
            'policy_id',
            sa.String(length=64),
            server_default='learning-v1',
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('learning_skill_experiences', 'policy_id')
    op.drop_column('curriculum_activities', 'required_concept_ids')
    op.drop_column('curriculum_materials', 'concept_ids')
    op.drop_index(
        'ix_curriculum_concept_competency_position',
        table_name='curriculum_concepts',
    )
    op.drop_table('curriculum_concepts')
