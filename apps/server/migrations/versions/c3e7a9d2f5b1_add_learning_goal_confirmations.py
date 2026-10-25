"""add learning goal confirmations

Revision ID: c3e7a9d2f5b1
Revises: b8d1f3a2c4e6
Create Date: 2026-10-20 22:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision: str = 'c3e7a9d2f5b1'
down_revision: str | None = 'b8d1f3a2c4e6'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # One row per confirmed Planner proposal: the same confirmation key returns the
    # same Goal instead of creating another one, even after the Redis planning expired.
    op.create_table(
        'learning_goal_confirmations',
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('confirmation_key', sa.String(length=36), nullable=False),
        sa.Column('planning_id', sa.String(length=26), nullable=False),
        sa.Column('goal_id', sa.String(length=26), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['goal_id'],
            ['learning_goals.id'],
            name='fk_learning_goal_confirmation_goal_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('account_id', 'confirmation_key'),
    )
    op.create_index(
        'ix_learning_goal_confirmation_goal_id',
        'learning_goal_confirmations',
        ['goal_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_learning_goal_confirmation_goal_id',
        table_name='learning_goal_confirmations',
    )
    op.drop_table('learning_goal_confirmations')
