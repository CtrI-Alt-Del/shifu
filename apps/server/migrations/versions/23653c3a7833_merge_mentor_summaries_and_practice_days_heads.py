"""merge mentor summaries and practice days migration heads

Revision ID: 23653c3a7833
Revises: 190822048e6a, f01033e9cd81
"""

from collections.abc import Sequence


revision: str = '23653c3a7833'
down_revision: tuple[str, str] = ('190822048e6a', 'f01033e9cd81')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
