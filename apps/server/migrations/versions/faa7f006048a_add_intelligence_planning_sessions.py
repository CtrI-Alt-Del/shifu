"""add_intelligence_planning_sessions

Revision ID: faa7f006048a
Revises: c4d82f1e7a30
Create Date: 2026-09-20 20:28:21.018703

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'faa7f006048a'
down_revision: str | None = 'c4d82f1e7a30'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'intelligence_planning_sessions',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('initial_intent', sa.String(length=4000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('intelligence_planning_sessions')
