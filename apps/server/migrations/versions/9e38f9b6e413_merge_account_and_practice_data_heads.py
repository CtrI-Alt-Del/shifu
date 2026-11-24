"""merge account and practice data heads

Revision ID: 9e38f9b6e413
Revises: 31fd929ad067, e48385bfd6fe
Create Date: 2026-11-22 22:28:04.064698

"""
from collections.abc import Sequence


revision: str = '9e38f9b6e413'
down_revision: tuple[str, str] = ('31fd929ad067', 'e48385bfd6fe')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
