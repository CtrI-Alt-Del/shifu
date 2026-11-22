"""Merge account appearance and ordering heads.

Revision ID: 7d3a9e5c1b48
Revises: 14fadc960949, 46a3cef1cbec
"""

revision: str = '7d3a9e5c1b48'
down_revision: tuple[str, str] = ('14fadc960949', '46a3cef1cbec')
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
