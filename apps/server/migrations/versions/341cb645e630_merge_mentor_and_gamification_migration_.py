"""merge mentor and gamification migration heads

Revision ID: 341cb645e630
Revises: 48176fc43cf2, a2f91c6d8e47
Create Date: 2026-10-12 11:40:50.684354

"""

from collections.abc import Sequence


revision: str = '341cb645e630'
down_revision: str | None = ('48176fc43cf2', 'a2f91c6d8e47')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
