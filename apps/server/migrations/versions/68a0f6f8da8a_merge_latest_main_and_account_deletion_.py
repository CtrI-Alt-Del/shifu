"""merge latest main and account deletion heads

Revision ID: 68a0f6f8da8a
Revises: 9e38f9b6e413, 2774ae48a022
Create Date: 2026-11-23 08:06:18.230302

"""

from collections.abc import Sequence


revision: str = '68a0f6f8da8a'
down_revision: str | None = ('9e38f9b6e413', '2774ae48a022')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
