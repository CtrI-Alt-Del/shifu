"""create practice days

Revision ID: f01033e9cd81
Revises: 341cb645e630
Create Date: 2026-10-15 00:59:15.749191

"""

import sqlalchemy as sa
from alembic import op

revision: str = 'f01033e9cd81'
down_revision: str | None = '341cb645e630'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        'gamification_practice_days',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('practice_date', sa.Date(), nullable=False),
        sa.Column('time_zone', sa.String(length=64), nullable=False),
        sa.Column('practiced_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recognized_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'practice_date',
            name='uq_gamification_practice_day_account_date',
        ),
    )
    op.add_column(
        'learning_activity_attempts',
        sa.Column('time_zone', sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('learning_activity_attempts', 'time_zone')
    op.drop_table('gamification_practice_days')
