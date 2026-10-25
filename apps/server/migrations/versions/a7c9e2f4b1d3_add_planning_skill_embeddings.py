"""add planning skill embeddings

Revision ID: a7c9e2f4b1d3
Revises: f01033e9cd81
Create Date: 2026-10-20 16:40:00.000000

"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = 'a7c9e2f4b1d3'
down_revision: str | None = 'f01033e9cd81'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'intelligence_planning_embedding_versions',
        sa.Column('version', sa.String(length=128), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('version'),
    )
    op.create_table(
        'intelligence_planning_skill_embeddings',
        sa.Column('version', sa.String(length=128), nullable=False),
        sa.Column('skill_id', sa.String(length=128), nullable=False),
        sa.Column('vector', Vector(384), nullable=False),
        sa.ForeignKeyConstraint(
            ['version'],
            ['intelligence_planning_embedding_versions.version'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('version', 'skill_id'),
    )


def downgrade() -> None:
    op.drop_table('intelligence_planning_skill_embeddings')
    op.drop_table('intelligence_planning_embedding_versions')
