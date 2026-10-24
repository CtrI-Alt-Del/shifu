"""Merge the Activity XP and learner memory migration heads."""

from collections.abc import Sequence


revision: str = 'd745b90dc652'
down_revision: tuple[str, str] = ('e862236a33c8', 'fdae74f2bef2')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
