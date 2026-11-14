"""Preserve the initiating session atomically on password change.

Revision ID: b16c32618ca8
Revises: 5d2b9e8c41a7
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'b16c32618ca8'
down_revision: str | None = '5d2b9e8c41a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'identity_accounts', sa.Column('retained_session_id', sa.Text(), nullable=True)
    )
    op.add_column(
        'identity_accounts',
        sa.Column('retained_session_access_version', sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        'ck_identity_accounts_retained_session',
        'identity_accounts',
        '(retained_session_id IS NULL AND retained_session_access_version IS NULL) OR '
        "(retained_session_id IS NOT NULL AND retained_session_id <> '' AND "
        'retained_session_access_version IS NOT NULL AND '
        'retained_session_access_version > 0 AND '
        'retained_session_access_version < access_version)',
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_identity_accounts_retained_session', 'identity_accounts', type_='check'
    )
    op.drop_column('identity_accounts', 'retained_session_access_version')
    op.drop_column('identity_accounts', 'retained_session_id')
