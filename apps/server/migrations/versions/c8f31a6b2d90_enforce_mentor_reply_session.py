"""enforce same-session mentor replies

Revision ID: c8f31a6b2d90
Revises: be8239ca8cfb
Create Date: 2026-10-08 23:00:00.000000

"""

from collections.abc import Sequence

from alembic import op


revision: str = 'c8f31a6b2d90'
down_revision: str | None = 'be8239ca8cfb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_mentor_message_session_id',
        'intelligence_mentor_messages',
        ['session_id', 'id'],
    )
    op.drop_constraint(
        'intelligence_mentor_messages_in_reply_to_message_id_fkey',
        'intelligence_mentor_messages',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'fk_mentor_message_reply_same_session',
        'intelligence_mentor_messages',
        'intelligence_mentor_messages',
        ['session_id', 'in_reply_to_message_id'],
        ['session_id', 'id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_mentor_message_reply_same_session',
        'intelligence_mentor_messages',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'intelligence_mentor_messages_in_reply_to_message_id_fkey',
        'intelligence_mentor_messages',
        'intelligence_mentor_messages',
        ['in_reply_to_message_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.drop_constraint(
        'uq_mentor_message_session_id',
        'intelligence_mentor_messages',
        type_='unique',
    )
