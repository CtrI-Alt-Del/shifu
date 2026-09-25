"""Merge the adaptive Learning and main application migration heads."""

from collections.abc import Sequence


revision: str = 'c9e4f6a7b8c1'
down_revision: tuple[str, str] = ('b8d93e4f6a12', 'f4a2c7d1e9b0')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
