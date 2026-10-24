"""Add private Mentor learner memories, their change records and deletion fences.

Revision ID: e862236a33c8
Revises: 23653c3a7833
Create Date: 2026-10-21 12:00:00.000000

Memories, origins, concepts, change records and one deletion fence per account are
Intelligence-owned. The learner message gains the memory analysis receipt. There is
no backfill: memories are created only from messages analyzed after this revision.
The downgrade drops the new tables and the two message columns; the memory data is
derived from learner statements and is not preserved.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'e862236a33c8'
down_revision: str | Sequence[str] | None = '23653c3a7833'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEMORIES = 'intelligence_learner_memories'
_ORIGINS = 'intelligence_learner_memory_origins'
_CONCEPTS = 'intelligence_learner_memory_concepts'
_CHANGES = 'intelligence_learner_memory_changes'
_FENCES = 'intelligence_learner_memory_fences'
_MESSAGES = 'intelligence_mentor_messages'
_CATEGORIES = (
    "category IN ('explanation_preference', 'declared_knowledge', "
    "'interest_or_intention', 'recurring_difficulty')"
)


def upgrade() -> None:
    op.create_table(
        _MEMORIES,
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_search', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('last_declared_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_CATEGORIES, name='ck_mentor_memory_category'),
        sa.CheckConstraint(
            'char_length(content) BETWEEN 1 AND 280',
            name='ck_mentor_memory_content_length',
        ),
        sa.CheckConstraint('version >= 1', name='ck_mentor_memory_version'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_mentor_memory_account_updated',
        _MEMORIES,
        ['account_id', sa.text('updated_at DESC'), 'id'],
        unique=False,
    )

    op.create_table(
        _ORIGINS,
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('memory_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('message_id', sa.String(length=26), nullable=True),
        sa.Column('declared_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], [f'{_MEMORIES}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['intelligence_mentor_sessions.id']),
        sa.ForeignKeyConstraint(
            ['message_id'], [f'{_MESSAGES}.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_mentor_memory_origin_memory',
        _ORIGINS,
        ['memory_id', 'declared_at'],
        unique=False,
    )
    op.create_index(
        'ix_mentor_memory_origin_message', _ORIGINS, ['message_id'], unique=False
    )
    op.create_index(
        'uq_mentor_memory_origin_message',
        _ORIGINS,
        ['memory_id', 'message_id'],
        unique=True,
        postgresql_where=sa.text('message_id IS NOT NULL'),
    )

    op.create_table(
        _CONCEPTS,
        sa.Column('memory_id', sa.String(length=26), nullable=False),
        sa.Column('concept_key', sa.String(length=80), nullable=False),
        sa.Column('label', sa.String(length=80), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            'position BETWEEN 0 AND 2', name='ck_mentor_memory_concept_position'
        ),
        sa.ForeignKeyConstraint(['memory_id'], [f'{_MEMORIES}.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('memory_id', 'concept_key'),
    )

    op.create_table(
        _CHANGES,
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('memory_id', sa.String(length=26), nullable=True),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('message_id', sa.String(length=26), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('previous_content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_CATEGORIES, name='ck_mentor_memory_change_category'),
        sa.CheckConstraint(
            "kind <> 'created' OR previous_content IS NULL",
            name='ck_mentor_memory_change_created',
        ),
        sa.CheckConstraint(
            'memory_id IS NOT NULL OR (content IS NULL AND previous_content IS NULL)',
            name='ck_mentor_memory_change_erased',
        ),
        sa.CheckConstraint(
            "kind IN ('created', 'updated')", name='ck_mentor_memory_change_kind'
        ),
        sa.ForeignKeyConstraint(
            ['memory_id'], [f'{_MEMORIES}.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['session_id'], ['intelligence_mentor_sessions.id']),
        sa.ForeignKeyConstraint(
            ['message_id'], [f'{_MESSAGES}.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_mentor_memory_change_account', _CHANGES, ['account_id'], unique=False
    )
    op.create_index(
        'ix_mentor_memory_change_memory', _CHANGES, ['memory_id'], unique=False
    )
    op.create_index(
        'ix_mentor_memory_change_message', _CHANGES, ['message_id'], unique=False
    )
    op.create_index(
        'ix_mentor_memory_change_session',
        _CHANGES,
        ['session_id', 'created_at'],
        unique=False,
    )

    op.create_table(
        _FENCES,
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('deleted_through', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('account_id'),
    )

    op.add_column(
        _MESSAGES,
        sa.Column('memory_analyzed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        _MESSAGES,
        sa.Column(
            'memory_statement_only',
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column(_MESSAGES, 'memory_statement_only')
    op.drop_column(_MESSAGES, 'memory_analyzed_at')

    op.drop_table(_FENCES)

    op.drop_index('ix_mentor_memory_change_session', table_name=_CHANGES)
    op.drop_index('ix_mentor_memory_change_message', table_name=_CHANGES)
    op.drop_index('ix_mentor_memory_change_memory', table_name=_CHANGES)
    op.drop_index('ix_mentor_memory_change_account', table_name=_CHANGES)
    op.drop_table(_CHANGES)

    op.drop_table(_CONCEPTS)

    op.drop_index(
        'uq_mentor_memory_origin_message',
        table_name=_ORIGINS,
        postgresql_where=sa.text('message_id IS NOT NULL'),
    )
    op.drop_index('ix_mentor_memory_origin_message', table_name=_ORIGINS)
    op.drop_index('ix_mentor_memory_origin_memory', table_name=_ORIGINS)
    op.drop_table(_ORIGINS)

    op.drop_index('ix_mentor_memory_account_updated', table_name=_MEMORIES)
    op.drop_table(_MEMORIES)
