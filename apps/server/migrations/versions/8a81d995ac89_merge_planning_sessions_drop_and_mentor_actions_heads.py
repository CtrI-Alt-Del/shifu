"""Merge the Planner sessions drop and the Mentor confirmed actions migration heads."""

from collections.abc import Sequence


revision: str = '8a81d995ac89'
down_revision: tuple[str, str] = ('b3c1f0a7d295', 'b8d1f3a2c4e6')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
