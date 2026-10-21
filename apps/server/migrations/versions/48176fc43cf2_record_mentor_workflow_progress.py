"""Record the current Mentor workflow step.

Revision ID: 48176fc43cf2
Revises: d8ace8901ed8
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '48176fc43cf2'
down_revision: str | None = 'd8ace8901ed8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'intelligence_mentor_response_events',
        sa.Column('progress', sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        'ck_mentor_event_progress',
        'intelligence_mentor_response_events',
        "progress IS NULL OR (kind = 'status' AND status = 'processing' AND progress IN ('write-answer','review-answer'))",
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_mentor_event_progress', 'intelligence_mentor_response_events', type_='check'
    )
    op.drop_column('intelligence_mentor_response_events', 'progress')
