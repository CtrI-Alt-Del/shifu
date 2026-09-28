"""Merge password recovery and diagnostic migration heads."""

from collections.abc import Sequence


revision: str = 'cddf4217a4b7'
down_revision: tuple[str, str] = ('e7b5c8d9f012', 'e8d45a1b9c03')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
