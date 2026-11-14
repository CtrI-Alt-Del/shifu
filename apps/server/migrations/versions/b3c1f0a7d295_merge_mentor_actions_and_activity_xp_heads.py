"""Merge the Mentor confirmed actions and Activity XP migration heads."""

from collections.abc import Sequence


revision: str = 'b3c1f0a7d295'
down_revision: tuple[str, str] = ('847da98f9bb2', 'd745b90dc652')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
