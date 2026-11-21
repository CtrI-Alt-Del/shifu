"""add account appearance

Revision ID: 14fadc960949
Revises: 4316ce01866a
Create Date: 2026-11-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '14fadc960949'
down_revision: str | None = '4316ce01866a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'identity_accounts',
        sa.Column(
            'appearance',
            sa.String(length=16),
            server_default='system',
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'ck_identity_accounts_appearance',
        'identity_accounts',
        "appearance IN ('dark', 'light', 'system')",
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_identity_accounts_appearance', 'identity_accounts', type_='check'
    )
    op.drop_column('identity_accounts', 'appearance')
