"""Persist identity-owned external effect receipts.

Revision ID: b6f1d6a0c49e
Revises: 8c98f10d2a64
Create Date: 2026-11-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b6f1d6a0c49e'
down_revision: str | Sequence[str] | None = '8c98f10d2a64'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'identity_account_external_effect_receipts',
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('effect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation', sa.String(length=120), nullable=False),
        sa.Column(
            'admitted_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'state',
            sa.String(length=16),
            server_default=sa.text("'in_flight'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('in_flight', 'settled', 'unknown')",
            name='ck_identity_account_external_effect_receipts_state',
        ),
        sa.CheckConstraint(
            'length(trim(operation)) BETWEEN 1 AND 120',
            name='ck_identity_account_external_effect_receipts_operation',
        ),
        sa.PrimaryKeyConstraint(
            'account_id',
            'effect_id',
            name='pk_identity_account_external_effect_receipts',
        ),
    )
    op.create_index(
        'ix_identity_account_external_effect_receipts_account_state',
        'identity_account_external_effect_receipts',
        ['account_id', 'state'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_identity_account_external_effect_receipts_account_state',
        table_name='identity_account_external_effect_receipts',
    )
    op.drop_table('identity_account_external_effect_receipts')
