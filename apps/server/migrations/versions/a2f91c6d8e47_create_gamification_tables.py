"""create_gamification_tables

Revision ID: a2f91c6d8e47
Revises: ba1d8c9e2f34
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a2f91c6d8e47'
down_revision: str | None = 'ba1d8c9e2f34'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'gamification_profiles',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('total_xp', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column(
            'streak_current', sa.Integer(), server_default='0', nullable=False
        ),
        sa.Column(
            'streak_longest', sa.Integer(), server_default='0', nullable=False
        ),
        sa.Column('streak_latest_practice_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_gamification_profile_account_id',
        'gamification_profiles',
        ['account_id'],
        unique=True,
    )

    op.create_table(
        'gamification_xp_grants',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('fact_id', sa.String(length=26), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('origin', sa.JSON(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_gamification_xp_grant_account_id',
        'gamification_xp_grants',
        ['account_id'],
    )

    op.create_table(
        'gamification_earned_achievements',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('achievement_id', sa.String(length=80), nullable=False),
        sa.Column('achievement_name', sa.String(length=120), nullable=False),
        sa.Column('criterion', sa.JSON(), nullable=False),
        sa.Column('xp_reward', sa.Integer(), nullable=False),
        sa.Column('achieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'achievement_id',
            name='uq_gamification_earned_achievement_account_achievement',
        ),
    )
    op.create_index(
        'ix_gamification_earned_achievement_account_id',
        'gamification_earned_achievements',
        ['account_id'],
    )

    op.create_table(
        'gamification_rewarded_milestones',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('fact_id', sa.String(length=26), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('subject_id', sa.String(length=26), nullable=False),
        sa.Column('xp_grant_id', sa.String(length=26), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rewarded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'kind',
            'subject_id',
            name='uq_gamification_rewarded_milestone_account_kind_subject',
        ),
    )
    op.create_index(
        'ix_gamification_rewarded_milestone_account_id',
        'gamification_rewarded_milestones',
        ['account_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_gamification_rewarded_milestone_account_id',
        table_name='gamification_rewarded_milestones',
    )
    op.drop_table('gamification_rewarded_milestones')

    op.drop_index(
        'ix_gamification_earned_achievement_account_id',
        table_name='gamification_earned_achievements',
    )
    op.drop_table('gamification_earned_achievements')

    op.drop_index(
        'ix_gamification_xp_grant_account_id',
        table_name='gamification_xp_grants',
    )
    op.drop_table('gamification_xp_grants')

    op.drop_index(
        'ix_gamification_profile_account_id',
        table_name='gamification_profiles',
    )
    op.drop_table('gamification_profiles')
