"""drop intelligence planning sessions

Revision ID: b8d1f3a2c4e6
Revises: a7c9e2f4b1d3
Create Date: 2026-10-20 18:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision: str = 'b8d1f3a2c4e6'
down_revision: str | None = 'a7c9e2f4b1d3'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # The temporary planning state now lives in Redis with a TTL; the stub table
    # never held confirmed data, so dropping it loses nothing durable.
    op.drop_table('intelligence_planning_sessions')


def downgrade() -> None:
    op.create_table(
        'intelligence_planning_sessions',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('initial_intent', sa.String(length=4000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
