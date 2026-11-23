"""Add private Learning practice drafts and photos.

Revision ID: e48385bfd6fe
Revises: 46a3cef1cbec, 14fadc960949
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'e48385bfd6fe'
down_revision: str | Sequence[str] | None = ('46a3cef1cbec', '14fadc960949')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'learning_practice_drafts',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('skill_experience_id', sa.String(length=26), nullable=False),
        sa.Column('activity_id', sa.String(length=26), nullable=False),
        sa.Column('reflection', sa.Text(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'consumed')", name='ck_learning_practice_draft_status'
        ),
        sa.CheckConstraint('revision >= 0', name='ck_learning_practice_draft_revision'),
        sa.ForeignKeyConstraint(
            ['skill_experience_id'],
            ['learning_skill_experiences.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_learning_practice_draft_active_experience_activity',
        'learning_practice_drafts',
        ['skill_experience_id', 'activity_id'],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        'learning_practice_photos',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('owner_kind', sa.String(length=20), nullable=False),
        sa.Column('draft_id', sa.String(length=26), nullable=True),
        sa.Column('attempt_id', sa.String(length=26), nullable=True),
        sa.Column('record_key', sa.String(length=100), nullable=False),
        sa.Column('object_key', sa.String(length=255), nullable=False),
        sa.Column('media_type', sa.String(length=40), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False),
        sa.Column('upload_key', sa.String(length=36), nullable=False),
        sa.Column('removal_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(owner_kind = 'draft' AND draft_id IS NOT NULL AND attempt_id IS NULL) OR (owner_kind = 'attempt' AND draft_id IS NULL AND attempt_id IS NOT NULL)",
            name='ck_learning_practice_photo_owner',
        ),
        sa.CheckConstraint(
            "state IN ('uploading', 'ready', 'failed', 'removed')",
            name='ck_learning_practice_photo_state',
        ),
        sa.CheckConstraint('size_bytes > 0', name='ck_learning_practice_photo_size'),
        sa.ForeignKeyConstraint(
            ['attempt_id'], ['learning_activity_attempts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['draft_id'], ['learning_practice_drafts.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_learning_practice_photo_attempt',
        'learning_practice_photos',
        ['attempt_id'],
        unique=False,
    )
    op.create_index(
        'ix_learning_practice_photo_draft',
        'learning_practice_photos',
        ['draft_id'],
        unique=False,
    )
    op.create_index(
        'uq_learning_practice_photo_draft_live_record',
        'learning_practice_photos',
        ['draft_id', 'record_key'],
        unique=True,
        postgresql_where=sa.text("draft_id IS NOT NULL AND state <> 'removed'"),
    )
    op.create_index(
        'uq_learning_practice_photo_draft_upload_key',
        'learning_practice_photos',
        ['draft_id', 'upload_key'],
        unique=True,
        postgresql_where=sa.text('draft_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_learning_practice_photo_draft_upload_key',
        table_name='learning_practice_photos',
        postgresql_where=sa.text('draft_id IS NOT NULL'),
    )
    op.drop_index(
        'uq_learning_practice_photo_draft_live_record',
        table_name='learning_practice_photos',
        postgresql_where=sa.text("draft_id IS NOT NULL AND state <> 'removed'"),
    )
    op.drop_index(
        'ix_learning_practice_photo_draft', table_name='learning_practice_photos'
    )
    op.drop_index(
        'ix_learning_practice_photo_attempt', table_name='learning_practice_photos'
    )
    op.drop_table('learning_practice_photos')
    op.drop_index(
        'uq_learning_practice_draft_active_experience_activity',
        table_name='learning_practice_drafts',
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_table('learning_practice_drafts')
