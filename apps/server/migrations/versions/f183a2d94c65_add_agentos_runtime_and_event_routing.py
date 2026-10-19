"""Add private AgentOS schemas and destination-aware outbox routing.

Revision ID: f183a2d94c65
Revises: 341cb645e630
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f183a2d94c65'
down_revision: str | Sequence[str] | None = '341cb645e630'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RUNTIME_ROLE = 'shifu_agentos_runtime'
_SCHEMAS = ('agentos_intelligence', 'agentos_learning')


def _create_runtime_schema(schema: str) -> None:
    op.execute(sa.text(f'CREATE SCHEMA {schema}'))
    op.execute(
        sa.text(f'REVOKE CREATE ON SCHEMA {schema} FROM PUBLIC, {_RUNTIME_ROLE}')
    )

    op.create_table(
        'agentos_sessions',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('session_type', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column(
            'session_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('agent_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('team_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'workflow_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('session_id'),
        schema=schema,
    )
    op.create_index(
        'idx_agentos_sessions_session_type',
        'agentos_sessions',
        ['session_type'],
        schema=schema,
    )
    op.create_index(
        'idx_agentos_sessions_created_at',
        'agentos_sessions',
        ['created_at'],
        schema=schema,
    )

    op.create_table(
        'agentos_workflow_runs',
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('run_data', sa.JSON(), nullable=False),
        sa.Column('run_type', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.Column('run_index', sa.BigInteger(), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('parent_run_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['session_id'],
            [f'{schema}.agentos_sessions.session_id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('run_id'),
        schema=schema,
    )
    for column in (
        'run_type',
        'session_id',
        'created_at',
        'agent_id',
        'team_id',
        'user_id',
        'workflow_id',
        'status',
    ):
        op.create_index(
            f'idx_agentos_workflow_runs_{column}',
            'agentos_workflow_runs',
            [column],
            schema=schema,
        )
    op.create_index(
        'agno_runs_session_id_run_index',
        'agentos_workflow_runs',
        ['session_id', 'run_index'],
        schema=schema,
    )

    op.create_table(
        'agentos_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('component_type', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('deployment_id', sa.String(), nullable=True),
        sa.Column('component_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('attempt', sa.BigInteger(), nullable=False),
        sa.Column('max_attempts', sa.BigInteger(), nullable=False),
        sa.Column('available_at', sa.BigInteger(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('locked_by', sa.String(), nullable=True),
        sa.Column('locked_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
        sa.Column('completed_at', sa.BigInteger(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=schema,
    )
    for column in ('component_id', 'session_id', 'status', 'created_at'):
        op.create_index(
            f'idx_agentos_jobs_{column}',
            'agentos_jobs',
            [column],
            schema=schema,
        )
    op.create_index(
        'idx_agentos_jobs_status_available_at',
        'agentos_jobs',
        ['status', 'available_at'],
        schema=schema,
    )
    op.create_index(
        'agentos_jobs_uq_jobs_idempotency_key',
        'agentos_jobs',
        ['idempotency_key', 'user_id'],
        unique=True,
        schema=schema,
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )
    op.create_index(
        'agentos_jobs_uq_jobs_idempotency_key_anon',
        'agentos_jobs',
        ['idempotency_key'],
        unique=True,
        schema=schema,
        postgresql_where=sa.text('idempotency_key IS NOT NULL AND user_id IS NULL'),
    )

    op.create_table(
        'agentos_traces',
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('start_time', sa.String(), nullable=False),
        sa.Column('end_time', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('duration_ms', sa.BigInteger(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('agent_id', sa.String(), nullable=True),
        sa.Column('team_id', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('trace_id'),
        schema=schema,
    )
    for column in (
        'status',
        'start_time',
        'run_id',
        'session_id',
        'user_id',
        'agent_id',
        'team_id',
        'workflow_id',
        'created_at',
    ):
        op.create_index(
            f'idx_agentos_traces_{column}',
            'agentos_traces',
            [column],
            schema=schema,
        )

    op.create_table(
        'agentos_spans',
        sa.Column('span_id', sa.String(), nullable=False),
        sa.Column('span_kind', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('start_time', sa.String(), nullable=False),
        sa.Column('end_time', sa.String(), nullable=False),
        sa.Column('status_code', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('duration_ms', sa.BigInteger(), nullable=False),
        sa.Column('trace_id', sa.String(), nullable=False),
        sa.Column('parent_span_id', sa.String(), nullable=True),
        sa.Column(
            'attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['trace_id'],
            [f'{schema}.agentos_traces.trace_id'],
        ),
        sa.PrimaryKeyConstraint('span_id'),
        schema=schema,
    )
    for column in ('trace_id', 'parent_span_id', 'start_time', 'created_at'):
        op.create_index(
            f'idx_agentos_spans_{column}',
            'agentos_spans',
            [column],
            schema=schema,
        )

    op.execute(sa.text(f'GRANT USAGE ON SCHEMA {schema} TO {_RUNTIME_ROLE}'))
    op.execute(
        sa.text(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA '
            f'{schema} TO {_RUNTIME_ROLE}'
        )
    )


def upgrade() -> None:
    op.add_column(
        'events',
        sa.Column(
            'destination',
            sa.String(length=80),
            nullable=False,
            server_default=sa.text("'unrouted'"),
        ),
    )
    op.create_check_constraint(
        'ck_events_destination',
        'events',
        "destination IN ('unrouted', 'inngest', 'agentos:intelligence', "
        "'agentos:learning')",
    )
    op.create_index(
        'ix_events_destination_status_available_at',
        'events',
        ['destination', 'status', 'available_at'],
    )

    for schema in _SCHEMAS:
        _create_runtime_schema(schema)

    op.create_table(
        'intelligence_mentor_attachment_batches',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=True),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_by_message_id', sa.String(length=26), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            'generation > 0', name='ck_mentor_attachment_batch_generation'
        ),
        sa.ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_batch_session_owner',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'id', 'account_id', name='uq_mentor_attachment_batch_owner'
        ),
    )
    op.create_index(
        'ix_mentor_attachment_batch_expiry',
        'intelligence_mentor_attachment_batches',
        ['expires_at', 'id'],
    )
    op.create_index(
        'ix_mentor_attachment_batch_owner',
        'intelligence_mentor_attachment_batches',
        ['account_id', 'session_id'],
    )

    op.create_table(
        'intelligence_mentor_attachments',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('batch_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=True),
        sa.Column('message_id', sa.String(length=26), nullable=True),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('upload_key', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('media_type', sa.String(length=128), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('object_key', sa.String(length=512), nullable=False),
        sa.Column('preview_key', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('failure_code', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('execution_owner', sa.String(length=64), nullable=True),
        sa.Column('claim_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('analyzed_pages', sa.JSON(), nullable=False),
        sa.Column('illegible_pages', sa.JSON(), nullable=False),
        sa.Column('uninterpreted_pages', sa.JSON(), nullable=False),
        sa.CheckConstraint('generation > 0', name='ck_mentor_attachment_generation'),
        sa.CheckConstraint(
            'size_bytes BETWEEN 1 AND 10000000', name='ck_mentor_attachment_size'
        ),
        sa.CheckConstraint(
            "status IN ('uploading', 'processing', 'ready', 'partial', 'failed', 'removed')",
            name='ck_mentor_attachment_status',
        ),
        sa.CheckConstraint(
            '(session_id IS NULL AND message_id IS NULL) OR '
            '(session_id IS NOT NULL AND message_id IS NOT NULL)',
            name='ck_mentor_attachment_binding_pair',
        ),
        sa.CheckConstraint(
            'failure_code IS NULL OR length(failure_code) BETWEEN 1 AND 64',
            name='ck_mentor_attachment_failure_code',
        ),
        sa.ForeignKeyConstraint(
            ['session_id', 'account_id'],
            [
                'intelligence_mentor_sessions.id',
                'intelligence_mentor_sessions.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_session_owner',
        ),
        sa.ForeignKeyConstraint(
            ['batch_id', 'account_id'],
            [
                'intelligence_mentor_attachment_batches.id',
                'intelligence_mentor_attachment_batches.account_id',
            ],
            ondelete='CASCADE',
            name='fk_mentor_attachment_batch_owner',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'batch_id',
            'upload_key',
            name='uq_mentor_attachment_upload_replay',
        ),
        sa.UniqueConstraint('object_key', name='uq_mentor_attachment_object_key'),
    )
    op.create_index(
        'ix_mentor_attachment_batch_status',
        'intelligence_mentor_attachments',
        ['batch_id', 'status'],
    )
    op.create_index(
        'ix_mentor_attachment_message',
        'intelligence_mentor_attachments',
        ['session_id', 'message_id'],
    )
    op.create_index(
        'ix_mentor_attachment_claim',
        'intelligence_mentor_attachments',
        ['status', 'claim_expires_at'],
    )

    op.create_table(
        'intelligence_mentor_attachment_chunks',
        sa.Column('chunk_id', sa.String(length=26), nullable=False),
        sa.Column('attachment_id', sa.String(length=26), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('locator', sa.String(length=256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.CheckConstraint(
            'generation > 0', name='ck_mentor_attachment_chunk_generation'
        ),
        sa.CheckConstraint(
            'page_number IS NULL OR page_number > 0',
            name='ck_mentor_attachment_chunk_page',
        ),
        sa.ForeignKeyConstraint(
            ['attachment_id'],
            ['intelligence_mentor_attachments.id'],
            ondelete='CASCADE',
            name='fk_mentor_attachment_chunk_attachment',
        ),
        sa.PrimaryKeyConstraint('chunk_id'),
        sa.UniqueConstraint(
            'attachment_id',
            'generation',
            'locator',
            name='uq_mentor_attachment_chunk_locator',
        ),
    )
    op.create_index(
        'ix_mentor_attachment_chunk_generation',
        'intelligence_mentor_attachment_chunks',
        ['attachment_id', 'generation'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_mentor_attachment_chunk_generation',
        table_name='intelligence_mentor_attachment_chunks',
    )
    op.drop_table('intelligence_mentor_attachment_chunks')
    op.drop_index(
        'ix_mentor_attachment_claim', table_name='intelligence_mentor_attachments'
    )
    op.drop_index(
        'ix_mentor_attachment_message', table_name='intelligence_mentor_attachments'
    )
    op.drop_index(
        'ix_mentor_attachment_batch_status',
        table_name='intelligence_mentor_attachments',
    )
    op.drop_table('intelligence_mentor_attachments')
    op.drop_index(
        'ix_mentor_attachment_batch_owner',
        table_name='intelligence_mentor_attachment_batches',
    )
    op.drop_index(
        'ix_mentor_attachment_batch_expiry',
        table_name='intelligence_mentor_attachment_batches',
    )
    op.drop_table('intelligence_mentor_attachment_batches')

    op.drop_index(
        'ix_events_destination_status_available_at',
        table_name='events',
    )
    op.drop_constraint('ck_events_destination', 'events', type_='check')
    op.drop_column('events', 'destination')

    for schema in reversed(_SCHEMAS):
        op.execute(sa.text(f'DROP SCHEMA {schema} CASCADE'))
