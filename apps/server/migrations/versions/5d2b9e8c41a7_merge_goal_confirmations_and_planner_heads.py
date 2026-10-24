"""Merge the SHIFU-95 goal confirmations and the integrated Planner heads."""

from collections.abc import Sequence


revision: str = '5d2b9e8c41a7'
down_revision: tuple[str, str] = ('7447a93e3e5d', 'c3e7a9d2f5b1')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
