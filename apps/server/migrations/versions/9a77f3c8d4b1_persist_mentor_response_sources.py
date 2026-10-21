"""Persist attachment sources on Mentor response blocks.

Revision ID: 9a77f3c8d4b1
Revises: f183a2d94c65
Create Date: 2026-10-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '9a77f3c8d4b1'
down_revision: str | Sequence[str] | None = 'f183a2d94c65'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'intelligence_mentor_response_events',
        sa.Column(
            'sources',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'ck_mentor_event_sources_shape',
        'intelligence_mentor_response_events',
        "jsonb_typeof(sources) = 'array' AND (kind = 'block' OR sources = '[]'::jsonb)",
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_mentor_event_sources_shape',
        'intelligence_mentor_response_events',
        type_='check',
    )
    op.drop_column('intelligence_mentor_response_events', 'sources')
