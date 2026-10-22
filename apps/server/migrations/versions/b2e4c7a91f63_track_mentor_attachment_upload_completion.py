"""Track durable completion of Mentor attachment uploads.

Revision ID: b2e4c7a91f63
Revises: 9a77f3c8d4b1
Create Date: 2026-10-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'b2e4c7a91f63'
down_revision: str | Sequence[str] | None = '9a77f3c8d4b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'intelligence_mentor_attachments',
        sa.Column('upload_completed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('intelligence_mentor_attachments', 'upload_completed_at')
