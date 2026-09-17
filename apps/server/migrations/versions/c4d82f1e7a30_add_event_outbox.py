"""add durable event outbox and committed notification

Revision ID: c4d82f1e7a30
Revises: b8f67e3c9a21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c4d82f1e7a30'
down_revision: str | None = 'b8f67e3c9a21'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'events',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            'status',
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            'attempts', sa.Integer(), server_default=sa.text('0'), nullable=False
        ),
        sa.Column(
            'available_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('reserved_by', sa.String(length=160), nullable=True),
        sa.Column('reservation_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_code', sa.String(length=80), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_events'),
        sa.CheckConstraint(
            "status IN ('pending', 'publishing', 'failed', 'published', 'terminal')",
            name='ck_events_status',
        ),
        sa.CheckConstraint('attempts >= 0', name='ck_events_attempts'),
    )
    op.create_index(
        'ix_events_status_available_at', 'events', ['status', 'available_at']
    )
    op.create_index(
        'ix_events_reservation_expires_at', 'events', ['reservation_expires_at']
    )
    op.create_index('ix_events_published_at', 'events', ['published_at'])
    op.execute(
        sa.text(
            """
            CREATE FUNCTION notify_shifu_event_insert()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                PERFORM pg_notify('shifu_events', NEW.id);
                RETURN NEW;
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_events_notify_after_insert
            AFTER INSERT ON events
            FOR EACH ROW
            EXECUTE FUNCTION notify_shifu_event_insert()
            """
        )
    )


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS trg_events_notify_after_insert ON events')
    op.execute('DROP FUNCTION IF EXISTS notify_shifu_event_insert()')
    op.drop_index('ix_events_published_at', table_name='events')
    op.drop_index('ix_events_reservation_expires_at', table_name='events')
    op.drop_index('ix_events_status_available_at', table_name='events')
    op.drop_table('events')
