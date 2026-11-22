"""Merge account deletion and current main schema heads.

Revision ID: b5b3086530f4
Revises: 46a3cef1cbec, d3b8c4e19a72
"""

revision: str = 'b5b3086530f4'
down_revision: tuple[str, str] = ('46a3cef1cbec', 'd3b8c4e19a72')
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
