"""remove_skill_experience_policy_id

Revision ID: e8d45a1b9c03
Revises: e7d45a1b9c02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e8d45a1b9c03'
down_revision: str | None = 'e7d45a1b9c02'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column('learning_skill_experiences', 'policy_id')


def downgrade() -> None:
    op.add_column(
        'learning_skill_experiences',
        sa.Column(
            'policy_id',
            sa.String(length=64),
            server_default='learning-v1',
            nullable=False,
        ),
    )
