"""create_activity_xp_tables

Revision ID: fdae74f2bef2
Revises: 23653c3a7833
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'fdae74f2bef2'
down_revision: str | None = '23653c3a7833'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'gamification_activity_xp_balances',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('activity_id', sa.String(length=26), nullable=False),
        sa.Column('maximum_xp', sa.Integer(), nullable=False),
        sa.Column('granted_xp', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'activity_id',
            name='uq_gamification_activity_xp_balance_account_activity',
        ),
    )
    op.create_index(
        'ix_gamification_activity_xp_balance_account_id',
        'gamification_activity_xp_balances',
        ['account_id'],
    )

    op.create_table(
        'gamification_activity_xp_recognitions',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('activity_id', sa.String(length=26), nullable=False),
        sa.Column('attempt_id', sa.String(length=26), nullable=False),
        sa.Column('granted_xp', sa.Integer(), nullable=False),
        sa.Column('xp_grant_id', sa.String(length=26), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recognized_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'attempt_id',
            name='uq_gamification_activity_xp_recognition_account_attempt',
        ),
    )
    op.create_index(
        'ix_gamification_activity_xp_recognition_account_id',
        'gamification_activity_xp_recognitions',
        ['account_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_gamification_activity_xp_recognition_account_id',
        table_name='gamification_activity_xp_recognitions',
    )
    op.drop_table('gamification_activity_xp_recognitions')

    op.drop_index(
        'ix_gamification_activity_xp_balance_account_id',
        table_name='gamification_activity_xp_balances',
    )
    op.drop_table('gamification_activity_xp_balances')
