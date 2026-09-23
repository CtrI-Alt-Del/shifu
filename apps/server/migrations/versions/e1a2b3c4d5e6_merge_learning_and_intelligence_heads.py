"""Merge the Learning and Intelligence migration heads.

Revision ID: e1a2b3c4d5e6
Revises: d72c0f4e8a31, faa7f006048a
"""

from collections.abc import Sequence


revision: str = 'e1a2b3c4d5e6'
down_revision: tuple[str, str] = ('d72c0f4e8a31', 'faa7f006048a')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
