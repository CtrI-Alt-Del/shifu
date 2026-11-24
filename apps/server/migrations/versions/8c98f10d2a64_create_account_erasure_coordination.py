"""Persist account erasure coordination and browser capabilities.

Revision ID: 8c98f10d2a64
Revises: ad56e779665a
Create Date: 2026-11-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8c98f10d2a64'
down_revision: str | Sequence[str] | None = 'ad56e779665a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'identity_account_erasures',
        sa.Column('erasure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=True),
        sa.Column(
            'status',
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed')",
            name='ck_identity_account_erasures_status',
        ),
        sa.PrimaryKeyConstraint('erasure_id', name='pk_identity_account_erasures'),
    )
    op.create_index(
        'ix_identity_account_erasures_pending_due',
        'identity_account_erasures',
        ['status', 'due_at'],
        unique=False,
    )

    op.create_table(
        'identity_account_erasure_participants',
        sa.Column('erasure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('participant', sa.String(length=80), nullable=False),
        sa.Column(
            'status',
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'acknowledged')",
            name='ck_identity_account_erasure_participants_status',
        ),
        sa.ForeignKeyConstraint(
            ['erasure_id'],
            ['identity_account_erasures.erasure_id'],
            name='fk_identity_account_erasure_participants_erasure_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint(
            'erasure_id',
            'participant',
            name='uq_identity_account_erasure_participants_erasure_participant',
        ),
    )

    op.create_table(
        'identity_account_browser_capabilities',
        sa.Column('capability_hash', sa.String(length=64), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column(
            'status',
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name='ck_identity_account_browser_capabilities_status',
        ),
        sa.PrimaryKeyConstraint(
            'capability_hash',
            name='pk_identity_account_browser_capabilities',
        ),
    )
    op.create_index(
        'ix_identity_account_browser_capabilities_account',
        'identity_account_browser_capabilities',
        ['account_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_identity_account_browser_capabilities_account',
        table_name='identity_account_browser_capabilities',
    )
    op.drop_table('identity_account_browser_capabilities')
    op.drop_table('identity_account_erasure_participants')
    op.drop_index(
        'ix_identity_account_erasures_pending_due',
        table_name='identity_account_erasures',
    )
    op.drop_table('identity_account_erasures')
