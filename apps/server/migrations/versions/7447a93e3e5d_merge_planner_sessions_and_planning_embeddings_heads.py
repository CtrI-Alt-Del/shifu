"""Merge the SHIFU-89 planning embeddings and SHIFU-91 Planner sessions heads."""

from collections.abc import Sequence


revision: str = '7447a93e3e5d'
down_revision: tuple[str, str] = ('835027bcdd9c', '8a81d995ac89')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
