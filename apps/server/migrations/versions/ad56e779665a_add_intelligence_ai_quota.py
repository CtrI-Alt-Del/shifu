"""add intelligence ai quota

Revision ID: ad56e779665a
Revises: b16c32618ca8
Create Date: 2026-11-11 18:07:31.687517

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'ad56e779665a'
down_revision: str | None = 'b16c32618ca8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'intelligence_ai_quota_months',
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('used_units', sa.BigInteger(), nullable=False),
        sa.Column('limit_units', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('account_id', 'month'),
        sa.CheckConstraint('used_units >= 0', name='ck_ai_quota_month_used_units'),
        sa.CheckConstraint('limit_units > 0', name='ck_ai_quota_month_limit_units'),
        sa.CheckConstraint(
            'EXTRACT(DAY FROM month) = 1', name='ck_ai_quota_month_first_day'
        ),
    )
    op.create_table(
        'intelligence_ai_quota_charges',
        sa.Column('request_kind', sa.String(length=32), nullable=False),
        sa.Column('request_id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('charged_units', sa.BigInteger(), nullable=False),
        sa.Column(
            'refunded', sa.Boolean(), server_default=sa.text('false'), nullable=False
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('request_kind', 'request_id'),
        sa.CheckConstraint(
            "request_kind IN ('mentor_response', 'planning_operation')",
            name='ck_ai_quota_charge_kind',
        ),
        sa.CheckConstraint(
            'charged_units >= 0', name='ck_ai_quota_charge_charged_units'
        ),
    )
    op.create_index(
        'ix_intelligence_ai_quota_charges_account_id',
        'intelligence_ai_quota_charges',
        ['account_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_intelligence_ai_quota_charges_account_id',
        table_name='intelligence_ai_quota_charges',
    )
    op.drop_table('intelligence_ai_quota_charges')
    op.drop_table('intelligence_ai_quota_months')
