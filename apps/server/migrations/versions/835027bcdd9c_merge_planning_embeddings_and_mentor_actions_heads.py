"""merge planning skill embeddings and mentor actions migration heads

Revision ID: 835027bcdd9c
Revises: a7c9e2f4b1d3, b3c1f0a7d295
"""

from collections.abc import Sequence


revision: str = '835027bcdd9c'
down_revision: tuple[str, str] = ('a7c9e2f4b1d3', 'b3c1f0a7d295')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
