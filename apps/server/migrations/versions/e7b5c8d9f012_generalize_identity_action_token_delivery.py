"""generalize action-token delivery correlation and expiry

Revision ID: e7b5c8d9f012
Revises: c9e4f6a7b8c1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b5c8d9f012'
down_revision: str | None = 'c9e4f6a7b8c1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        'uq_communication_messages_identity_confirmation_id',
        table_name='communication_messages',
    )
    op.alter_column(
        'communication_messages',
        'identity_confirmation_id',
        new_column_name='identity_action_token_id',
        existing_type=sa.String(length=26),
        existing_nullable=True,
    )
    op.add_column(
        'communication_messages',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            'UPDATE communication_messages AS communication '
            'SET expires_at = token.expires_at '
            'FROM identity_account_action_tokens AS token '
            'WHERE communication.identity_action_token_id = token.id '
            'AND communication.expires_at IS NULL'
        )
    )
    op.create_index(
        'uq_communication_messages_identity_action_token_id',
        'communication_messages',
        ['identity_action_token_id'],
        unique=True,
        postgresql_where=sa.text('identity_action_token_id IS NOT NULL'),
    )


def downgrade() -> None:
    raise RuntimeError(
        'This migration cannot be downgraded safely after action-token delivery rows exist.'
    )
