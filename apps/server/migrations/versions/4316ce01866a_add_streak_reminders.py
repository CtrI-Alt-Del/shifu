"""add streak reminders

Revision ID: 4316ce01866a
Revises: ad56e779665a
Create Date: 2026-11-18 12:07:41.717761

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4316ce01866a'
down_revision: Union[str, None] = 'ad56e779665a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'communication_push_subscriptions',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('endpoint', sa.String(length=2048), nullable=False),
        sa.Column('p256dh_key', sa.String(length=255), nullable=False),
        sa.Column('auth_secret', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'endpoint', name='uq_communication_push_subscriptions_endpoint'
        ),
    )
    op.create_index(
        'ix_communication_push_subscriptions_account_id',
        'communication_push_subscriptions',
        ['account_id'],
        unique=False,
    )
    op.create_table(
        'communication_streak_reminder_preferences',
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('account_id'),
    )
    op.create_table(
        'communication_streak_reminders',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('streak_days', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            'streak_days >= 1', name='ck_communication_streak_reminders_streak_days'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'local_date',
            name='uq_communication_streak_reminders_account_local_date',
        ),
    )
    op.create_index(
        'ix_communication_streak_reminders_account_status',
        'communication_streak_reminders',
        ['account_id', 'status'],
        unique=False,
    )
    op.create_table(
        'communication_push_deliveries',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('reminder_id', sa.String(length=26), nullable=False),
        sa.Column('subscription_id', sa.String(length=26), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_code', sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ['reminder_id'], ['communication_streak_reminders.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'reminder_id',
            'subscription_id',
            name='uq_communication_push_deliveries_reminder_subscription',
        ),
    )
    op.add_column(
        'gamification_profiles',
        sa.Column(
            'reminder_hour', sa.SmallInteger(), server_default='18', nullable=False
        ),
    )
    op.add_column(
        'gamification_profiles',
        sa.Column(
            'reminder_invite_answered_at', sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_check_constraint(
        'ck_gamification_profiles_reminder_hour',
        'gamification_profiles',
        'reminder_hour BETWEEN 6 AND 22',
    )
    op.create_index(
        'ix_gamification_profiles_streak_latest_practice_date',
        'gamification_profiles',
        ['streak_latest_practice_date'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_gamification_profiles_streak_latest_practice_date',
        table_name='gamification_profiles',
    )
    op.drop_constraint(
        'ck_gamification_profiles_reminder_hour', 'gamification_profiles', type_='check'
    )
    op.drop_column('gamification_profiles', 'reminder_invite_answered_at')
    op.drop_column('gamification_profiles', 'reminder_hour')
    op.drop_table('communication_push_deliveries')
    op.drop_index(
        'ix_communication_streak_reminders_account_status',
        table_name='communication_streak_reminders',
    )
    op.drop_table('communication_streak_reminders')
    op.drop_table('communication_streak_reminder_preferences')
    op.drop_index(
        'ix_communication_push_subscriptions_account_id',
        table_name='communication_push_subscriptions',
    )
    op.drop_table('communication_push_subscriptions')
