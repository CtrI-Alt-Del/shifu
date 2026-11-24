"""merge account appearance and account deletion heads

Revision ID: 31fd929ad067
Revises: 14fadc960949, b5b3086530f4
Create Date: 2026-11-22 14:10:30.894147

"""

from collections.abc import Sequence


revision: str = '31fd929ad067'
down_revision: str | None = ('14fadc960949', 'b5b3086530f4')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
