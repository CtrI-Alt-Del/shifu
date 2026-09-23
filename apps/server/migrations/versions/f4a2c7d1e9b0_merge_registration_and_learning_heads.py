"""merge registration and learning migration heads

Revision ID: f4a2c7d1e9b0
Revises: d7f4e9a1c2b3, e1a2b3c4d5e6
"""

from collections.abc import Sequence


revision: str = 'f4a2c7d1e9b0'
down_revision: tuple[str, str] = ('d7f4e9a1c2b3', 'e1a2b3c4d5e6')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
