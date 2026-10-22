"""Add Mentor conversation summaries and the summarize-context progress step.

Revision ID: 190822048e6a
Revises: b2e4c7a91f63
Create Date: 2026-10-18 14:13:54.641516

The downgrade fails safely, before changing the schema, when any response event
still records the ``summarize-context`` progress, because the previous
``ck_mentor_event_progress`` constraint would reject those rows. Summary rows are
derived data and are dropped with their table. There is no backfill.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '190822048e6a'
down_revision: str | Sequence[str] | None = 'b2e4c7a91f63'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENTS_TABLE = 'intelligence_mentor_response_events'
_SUMMARIES_TABLE = 'intelligence_mentor_session_summaries'
_PROGRESS_CHECK = 'ck_mentor_event_progress'
_PROGRESS_BEFORE = "progress IS NULL OR (kind = 'status' AND status = 'processing' AND progress IN ('write-answer','review-answer'))"
_PROGRESS_AFTER = "progress IS NULL OR (kind = 'status' AND status = 'processing' AND progress IN ('summarize-context','write-answer','review-answer'))"


def upgrade() -> None:
    op.create_table(
        _SUMMARIES_TABLE,
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('attempt_id', sa.String(length=26), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('boundary_message_id', sa.String(length=26), nullable=False),
        sa.Column('boundary_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_message_id', sa.String(length=26), nullable=False),
        sa.Column('covered_message_count', sa.Integer(), nullable=False),
        sa.Column('topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('excerpts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('algorithm_version', sa.String(length=64), nullable=True),
        sa.Column('failure_code', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'failed') = (failure_code IS NOT NULL)",
            name='ck_mentor_summary_failure',
        ),
        sa.CheckConstraint(
            "(status = 'ready') = (topics IS NOT NULL AND excerpts IS NOT NULL AND algorithm_version IS NOT NULL AND completed_at IS NOT NULL)",
            name='ck_mentor_summary_ready_content',
        ),
        sa.CheckConstraint(
            "failure_code IS NULL OR failure_code IN ('nlp_unavailable', 'invalid_output', 'exhausted')",
            name='ck_mentor_summary_failure_code',
        ),
        sa.CheckConstraint(
            "status <> 'processing' OR attempt_id IS NOT NULL",
            name='ck_mentor_summary_processing_attempt',
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'ready', 'failed')",
            name='ck_mentor_summary_status',
        ),
        sa.CheckConstraint(
            'covered_message_count > 0', name='ck_mentor_summary_covered_count'
        ),
        sa.CheckConstraint('version >= 1', name='ck_mentor_summary_version'),
        sa.ForeignKeyConstraint(
            ['attempt_id'],
            ['intelligence_mentor_response_attempts.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['boundary_message_id'],
            ['intelligence_mentor_messages.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['session_id'], ['intelligence_mentor_sessions.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'version', name='uq_mentor_summary_version'),
    )
    op.create_index(
        'ix_mentor_summary_account', _SUMMARIES_TABLE, ['account_id'], unique=False
    )
    op.create_index(
        'uq_mentor_summary_active',
        _SUMMARIES_TABLE,
        ['session_id'],
        unique=True,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.create_index(
        'uq_mentor_summary_ready',
        _SUMMARIES_TABLE,
        ['session_id'],
        unique=True,
        postgresql_where=sa.text("status = 'ready'"),
    )
    op.drop_constraint(_PROGRESS_CHECK, _EVENTS_TABLE, type_='check')
    op.create_check_constraint(_PROGRESS_CHECK, _EVENTS_TABLE, _PROGRESS_AFTER)


def downgrade() -> None:
    blocked = (
        op.get_bind()
        .execute(
            sa.text(
                'SELECT count(*) FROM intelligence_mentor_response_events '
                "WHERE progress = 'summarize-context'"
            )
        )
        .scalar_one()
    )
    if blocked:
        raise RuntimeError(
            'Cannot downgrade: response events still record the summarize-context '
            'progress. Remove those events before downgrading.'
        )

    op.drop_constraint(_PROGRESS_CHECK, _EVENTS_TABLE, type_='check')
    op.create_check_constraint(_PROGRESS_CHECK, _EVENTS_TABLE, _PROGRESS_BEFORE)
    op.drop_index(
        'uq_mentor_summary_ready',
        table_name=_SUMMARIES_TABLE,
        postgresql_where=sa.text("status = 'ready'"),
    )
    op.drop_index(
        'uq_mentor_summary_active',
        table_name=_SUMMARIES_TABLE,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.drop_index('ix_mentor_summary_account', table_name=_SUMMARIES_TABLE)
    op.drop_table(_SUMMARIES_TABLE)
