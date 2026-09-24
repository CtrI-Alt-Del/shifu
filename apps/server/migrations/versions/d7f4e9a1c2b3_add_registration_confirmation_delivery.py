"""add registration confirmation delivery persistence

Revision ID: d7f4e9a1c2b3
Revises: c4d82f1e7a30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd7f4e9a1c2b3'
down_revision: str | None = 'c4d82f1e7a30'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        'identity_accounts_email_key', 'identity_accounts', type_='unique'
    )
    op.create_index(
        'uq_identity_accounts_active_email',
        'identity_accounts',
        ['email'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    op.add_column(
        'identity_account_action_tokens',
        sa.Column('communication_id', sa.String(length=26), nullable=True),
    )
    op.add_column(
        'identity_account_action_tokens',
        sa.Column('pending_handle_hash', sa.String(length=64), nullable=True),
    )
    op.add_column(
        'identity_account_action_tokens',
        sa.Column('delivery_status', sa.String(length=40), nullable=True),
    )
    op.execute(
        sa.text(
            'UPDATE identity_account_action_tokens '
            'SET communication_id = id WHERE communication_id IS NULL'
        )
    )
    op.alter_column(
        'identity_account_action_tokens',
        'communication_id',
        existing_type=sa.String(length=26),
        nullable=False,
    )
    op.create_index(
        'ix_identity_account_action_tokens_pending_handle_hash',
        'identity_account_action_tokens',
        ['pending_handle_hash'],
        postgresql_where=sa.text('pending_handle_hash IS NOT NULL'),
    )
    op.create_index(
        'ix_identity_account_action_tokens_account_type_issued_at',
        'identity_account_action_tokens',
        ['account_id', 'type', 'issued_at'],
    )

    op.alter_column(
        'communication_messages',
        'recipient_email',
        existing_type=sa.String(length=320),
        nullable=True,
    )
    op.alter_column(
        'communication_messages',
        'content',
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.add_column(
        'communication_messages',
        sa.Column('identity_confirmation_id', sa.String(length=26), nullable=True),
    )
    op.add_column(
        'communication_messages',
        sa.Column('encrypted_content', sa.JSON(), nullable=True),
    )
    op.add_column(
        'communication_messages',
        sa.Column('redacted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'uq_communication_messages_identity_confirmation_id',
        'communication_messages',
        ['identity_confirmation_id'],
        unique=True,
        postgresql_where=sa.text('identity_confirmation_id IS NOT NULL'),
    )
    op.create_index(
        'ix_communication_messages_status_next_attempt_at',
        'communication_messages',
        ['status', 'next_attempt_at'],
    )
    op.create_unique_constraint(
        'uq_communication_delivery_attempts_communication_attempt',
        'communication_delivery_attempts',
        ['communication_id', 'attempt_number'],
    )


def downgrade() -> None:
    raise RuntimeError(
        'This migration cannot be downgraded safely after deleted e-mails are reused.'
    )
