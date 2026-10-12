"""add mentor contextual responses

Revision ID: e633a93a3930
Revises: c8f31a6b2d90
Create Date: 2026-10-10 14:30:15.645242

"""

from collections.abc import Sequence
from pgvector.sqlalchemy import Vector

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e633a93a3930'
down_revision: str | None = 'c8f31a6b2d90'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_unique_constraint(
        'uq_mentor_session_owner', 'intelligence_mentor_sessions', ['id', 'account_id']
    )
    op.create_table(
        'intelligence_mentor_embedding_versions',
        sa.Column('version', sa.String(length=128), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('version'),
    )
    op.create_table(
        'intelligence_mentor_indexed_embeddings',
        sa.Column('version', sa.String(length=128), nullable=False),
        sa.Column('corpus', sa.String(length=16), nullable=False),
        sa.Column('reference_id', sa.String(length=128), nullable=False),
        sa.Column('variation_key', sa.String(length=128), nullable=False),
        sa.Column('vector', Vector(384), nullable=False),
        sa.CheckConstraint(
            "corpus IN ('intents', 'answers', 'curriculum')",
            name='ck_mentor_embedding_corpus',
        ),
        sa.ForeignKeyConstraint(
            ['version'],
            ['intelligence_mentor_embedding_versions.version'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('version', 'corpus', 'reference_id', 'variation_key'),
    )
    op.create_table(
        'intelligence_mentor_response_attempts',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('learner_message_id', sa.String(length=26), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column(
            'context_hint', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('access_revision', sa.String(length=128), nullable=False),
        sa.Column('execution_owner', sa.String(length=26), nullable=True),
        sa.Column('execution_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'resolved_reference_ids',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            'generation_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column('operation_key', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name='ck_mentor_attempt_status',
        ),
        sa.ForeignKeyConstraint(
            ['session_id', 'learner_message_id'],
            [
                'intelligence_mentor_messages.session_id',
                'intelligence_mentor_messages.id',
            ],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('session_id', 'id', name='uq_mentor_attempt_session'),
        sa.ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_mentor_attempt_current',
        'intelligence_mentor_response_attempts',
        ['session_id', 'created_at', 'id'],
        unique=False,
    )
    op.create_index(
        'uq_mentor_active_attempt',
        'intelligence_mentor_response_attempts',
        ['session_id'],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )
    op.create_table(
        'intelligence_mentor_response_events',
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('attempt_id', sa.String(length=26), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('block_key', sa.String(length=128), nullable=True),
        sa.Column('ordinal', sa.Integer(), nullable=True),
        sa.Column('intent', sa.String(length=64), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('consultation', sa.String(length=32), nullable=True),
        sa.Column('failure_code', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['attempt_id'],
            ['intelligence_mentor_response_attempts.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['session_id'], ['intelligence_mentor_sessions.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['session_id', 'attempt_id'],
            [
                'intelligence_mentor_response_attempts.session_id',
                'intelligence_mentor_response_attempts.id',
            ],
            ondelete='CASCADE',
        ),
        sa.CheckConstraint(
            "kind IN ('status','consultation','block','completed','failed','cancelled')",
            name='ck_mentor_event_kind',
        ),
        sa.CheckConstraint(
            "status IN ('queued','processing','completed','failed','cancelled')",
            name='ck_mentor_event_status',
        ),
        sa.CheckConstraint('sequence > 0', name='ck_mentor_event_sequence'),
        sa.CheckConstraint(
            "consultation IS NULL OR consultation IN ('learning','curriculum','gamification')",
            name='ck_mentor_event_consultation',
        ),
        sa.CheckConstraint(
            "(kind = 'block' AND block_key IS NOT NULL AND ordinal >= 0 AND content IS NOT NULL) OR (kind <> 'block' AND block_key IS NULL AND ordinal IS NULL AND content IS NULL)",
            name='ck_mentor_event_block_shape',
        ),
        sa.PrimaryKeyConstraint('session_id', 'sequence'),
        sa.UniqueConstraint('attempt_id', 'block_key', name='uq_mentor_attempt_block'),
    )
    op.create_index(
        'uq_mentor_attempt_ordinal',
        'intelligence_mentor_response_events',
        ['attempt_id', 'ordinal'],
        unique=True,
        postgresql_where=sa.text("kind = 'block'"),
    )
    op.create_table(
        'intelligence_mentor_response_submissions',
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('submission_key', sa.String(length=36), nullable=False),
        sa.Column('attempt_id', sa.String(length=26), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ['attempt_id'],
            ['intelligence_mentor_response_attempts.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('account_id', 'session_id', 'submission_key'),
    )
    op.add_column(
        'intelligence_mentor_sessions',
        sa.Column(
            'response_sequence', sa.Integer(), server_default='0', nullable=False
        ),
    )
    # Legacy learner messages remain recoverable without dispatching new jobs.
    op.execute(
        sa.text("""
        INSERT INTO intelligence_mentor_response_attempts
            (id, account_id, session_id, learner_message_id, status, context_hint,
             access_revision, operation_key, created_at, updated_at,
             generation_keys, resolved_reference_ids)
        SELECT m.id, s.account_id, s.id, m.id, 'failed', NULL,
               'legacy-unverified', 'legacy:' || m.id, m.created_at,
               CURRENT_TIMESTAMP, '[]'::jsonb, '[]'::jsonb
        FROM intelligence_mentor_sessions s
        JOIN LATERAL (
            SELECT pending.id, pending.created_at
            FROM intelligence_mentor_messages pending
            WHERE pending.session_id = s.id AND pending.role = 'learner'
              AND NOT EXISTS (
                  SELECT 1 FROM intelligence_mentor_messages response
                  WHERE response.in_reply_to_message_id = pending.id
              )
            ORDER BY pending.created_at DESC, pending.id DESC LIMIT 1
        ) m ON TRUE
        WHERE s.deleted_at IS NULL
    """)
    )
    op.execute(
        sa.text("""
        INSERT INTO intelligence_mentor_response_events
            (session_id, sequence, attempt_id, kind, status, failure_code, created_at)
        SELECT session_id, 1, id, 'failed', 'failed', 'service_unavailable',
               CURRENT_TIMESTAMP
        FROM intelligence_mentor_response_attempts
    """)
    )
    op.execute(
        sa.text("""
        UPDATE intelligence_mentor_sessions SET response_sequence = 1
        WHERE id IN (SELECT session_id FROM intelligence_mentor_response_attempts)
    """)
    )


def downgrade() -> None:
    op.drop_column('intelligence_mentor_sessions', 'response_sequence')
    op.drop_table('intelligence_mentor_response_submissions')
    op.drop_index(
        'uq_mentor_attempt_ordinal',
        table_name='intelligence_mentor_response_events',
        postgresql_where=sa.text("kind = 'block'"),
    )
    op.drop_table('intelligence_mentor_response_events')
    op.drop_index(
        'uq_mentor_active_attempt',
        table_name='intelligence_mentor_response_attempts',
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )
    op.drop_index(
        'ix_mentor_attempt_current', table_name='intelligence_mentor_response_attempts'
    )
    op.drop_table('intelligence_mentor_response_attempts')
    op.drop_table('intelligence_mentor_indexed_embeddings')
    op.drop_table('intelligence_mentor_embedding_versions')
    op.drop_constraint(
        'uq_mentor_session_owner', 'intelligence_mentor_sessions', type_='unique'
    )
