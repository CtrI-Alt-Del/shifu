"""Merge account deletion durability migration heads.

Revision ID: d3b8c4e19a72
Revises: a10cf42957b3, a04e7f91c2d6, c2e7a9f6b4d1
"""

from collections.abc import Sequence

revision: str = 'd3b8c4e19a72'
down_revision: str | Sequence[str] | None = (
    'a10cf42957b3',
    'a04e7f91c2d6',
    'c2e7a9f6b4d1',
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
