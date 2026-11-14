"""add mentor action proposals and receipts

Revision ID: 847da98f9bb2
Revises: e862236a33c8
Create Date: 2026-10-23 21:05:24.616798

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '847da98f9bb2'
down_revision: str | None = 'e862236a33c8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'learning_mentor_action_receipts',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('confirmation_id', sa.String(length=26), nullable=False),
        sa.Column('operation', sa.String(length=16), nullable=False),
        sa.Column('goal_id', sa.String(length=26), nullable=False),
        sa.Column('skill_id', sa.String(length=26), nullable=True),
        sa.Column('skill_experience_id', sa.String(length=26), nullable=True),
        sa.Column('outcome', sa.String(length=16), nullable=False),
        sa.Column('rejection_reason', sa.String(length=32), nullable=True),
        sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(outcome = 'rejected') = (rejection_reason IS NOT NULL)",
            name='ck_learning_mentor_action_receipt_rejection_shape',
        ),
        sa.CheckConstraint(
            "operation IN ('add_skill','remove_skill')",
            name='ck_learning_mentor_action_receipt_operation',
        ),
        sa.CheckConstraint(
            "outcome IN ('added','already_present','removed','rejected')",
            name='ck_learning_mentor_action_receipt_outcome',
        ),
        sa.CheckConstraint(
            "rejection_reason IS NULL OR rejection_reason IN ('goal_unavailable','skill_unavailable','experience_unavailable')",
            name='ck_learning_mentor_action_receipt_rejection_reason',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'account_id',
            'confirmation_id',
            name='uq_learning_mentor_action_receipt_confirmation',
        ),
    )
    op.create_table(
        'intelligence_mentor_action_proposals',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('account_id', sa.String(length=26), nullable=False),
        sa.Column('session_id', sa.String(length=26), nullable=False),
        sa.Column('learner_message_id', sa.String(length=26), nullable=False),
        sa.Column('attempt_id', sa.String(length=26), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('outcome', sa.String(length=16), nullable=True),
        sa.Column('rejection_reason', sa.String(length=32), nullable=True),
        sa.Column('skill_id', sa.String(length=255), nullable=False),
        sa.Column('skill_name', sa.String(length=255), nullable=False),
        sa.Column('goal_id', sa.String(length=255), nullable=True),
        sa.Column('goal_title', sa.String(length=255), nullable=True),
        sa.Column('skill_experience_id', sa.String(length=255), nullable=True),
        sa.Column(
            'candidate_goals',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column('justification', sa.String(length=2000), nullable=True),
        sa.Column('resolved_goal_id', sa.String(length=255), nullable=True),
        sa.Column('resolved_skill_experience_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'completed') = (outcome IS NOT NULL) AND (status = 'rejected') = (rejection_reason IS NOT NULL)",
            name='ck_mentor_action_proposal_resolution',
        ),
        sa.CheckConstraint(
            "jsonb_typeof(candidate_goals) = 'array'",
            name='ck_mentor_action_proposal_candidates',
        ),
        sa.CheckConstraint(
            "kind IN ('add_skill', 'remove_skill')",
            name='ck_mentor_action_proposal_kind',
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('added', 'already_present', 'removed')",
            name='ck_mentor_action_proposal_outcome',
        ),
        sa.CheckConstraint(
            "rejection_reason IS NULL OR rejection_reason IN ('goal_unavailable', 'skill_unavailable', 'experience_unavailable')",
            name='ck_mentor_action_proposal_rejection_reason',
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'declined', 'completed', 'rejected')",
            name='ck_mentor_action_proposal_status',
        ),
        sa.ForeignKeyConstraint(
            ['attempt_id'],
            ['intelligence_mentor_response_attempts.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['learner_message_id'],
            ['intelligence_mentor_messages.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['session_id'], ['intelligence_mentor_sessions.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_mentor_action_proposal_attempt',
        'intelligence_mentor_action_proposals',
        ['attempt_id'],
        unique=False,
    )
    op.create_index(
        'ix_mentor_action_proposal_session_status',
        'intelligence_mentor_action_proposals',
        ['account_id', 'session_id', 'status'],
        unique=False,
    )
    op.add_column(
        'intelligence_mentor_response_events',
        sa.Column('action_proposal_id', sa.String(length=26), nullable=True),
    )
    op.create_foreign_key(
        'intelligence_mentor_response_events_action_proposal_id_fkey',
        'intelligence_mentor_response_events',
        'intelligence_mentor_action_proposals',
        ['action_proposal_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.drop_constraint(
        'ck_mentor_event_kind', 'intelligence_mentor_response_events', type_='check'
    )
    op.create_check_constraint(
        'ck_mentor_event_kind',
        'intelligence_mentor_response_events',
        "kind IN ('status','consultation','block','completed','failed','cancelled','action')",
    )
    op.create_check_constraint(
        'ck_mentor_event_action_shape',
        'intelligence_mentor_response_events',
        "(kind = 'action') = (action_proposal_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM intelligence_mentor_response_events WHERE kind = 'action'")
    op.drop_constraint(
        'ck_mentor_event_action_shape',
        'intelligence_mentor_response_events',
        type_='check',
    )
    op.drop_constraint(
        'ck_mentor_event_kind', 'intelligence_mentor_response_events', type_='check'
    )
    op.drop_constraint(
        'intelligence_mentor_response_events_action_proposal_id_fkey',
        'intelligence_mentor_response_events',
        type_='foreignkey',
    )
    op.drop_column('intelligence_mentor_response_events', 'action_proposal_id')
    op.drop_index(
        'ix_mentor_action_proposal_session_status',
        table_name='intelligence_mentor_action_proposals',
    )
    op.drop_index(
        'ix_mentor_action_proposal_attempt',
        table_name='intelligence_mentor_action_proposals',
    )
    op.drop_table('intelligence_mentor_action_proposals')
    op.drop_table('learning_mentor_action_receipts')
    op.create_check_constraint(
        'ck_mentor_event_kind',
        'intelligence_mentor_response_events',
        "kind IN ('status','consultation','block','completed','failed','cancelled')",
    )
