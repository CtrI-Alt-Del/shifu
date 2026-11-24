"""Create the audited Identity external-effect reconciliation table."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c2e7a9f6b4d1'
down_revision: str | Sequence[str] | None = 'b6f1d6a0c49e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'identity_account_external_effect_reconciliations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('effect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation', sa.String(length=120), nullable=False),
        sa.Column('previous_state', sa.String(length=16), nullable=False),
        sa.Column('resolution', sa.String(length=16), nullable=False),
        sa.Column('operator_id', sa.String(length=64), nullable=False),
        sa.Column('evidence_reference', sa.String(length=160), nullable=False),
        sa.Column('evidence_sha256', sa.String(length=64), nullable=False),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "previous_state IN ('in_flight', 'unknown')",
            name='ck_identity_external_effect_reconciliations_previous_state',
        ),
        sa.CheckConstraint(
            "resolution IN ('applied', 'not_applied')",
            name='ck_identity_external_effect_reconciliations_resolution',
        ),
        sa.CheckConstraint(
            'length(trim(operation)) BETWEEN 1 AND 120',
            name='ck_identity_external_effect_reconciliations_operation',
        ),
        sa.CheckConstraint(
            'length(trim(operator_id)) BETWEEN 1 AND 64',
            name='ck_identity_external_effect_reconciliations_operator',
        ),
        sa.CheckConstraint(
            'length(trim(evidence_reference)) BETWEEN 1 AND 160',
            name='ck_identity_external_effect_reconciliations_evidence_reference',
        ),
        sa.CheckConstraint(
            'length(evidence_sha256) = 64',
            name='ck_identity_external_effect_reconciliations_evidence_sha256',
        ),
        sa.PrimaryKeyConstraint(
            'id', name='pk_identity_external_effect_reconciliations'
        ),
    )
    op.create_index(
        'ix_identity_external_effect_reconciliations_effect_time',
        'identity_account_external_effect_reconciliations',
        ['effect_id', 'reconciled_at'],
        unique=False,
    )
    op.create_index(
        'ix_identity_external_effect_reconciliations_time',
        'identity_account_external_effect_reconciliations',
        ['reconciled_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_identity_external_effect_reconciliations_time',
        table_name='identity_account_external_effect_reconciliations',
    )
    op.drop_index(
        'ix_identity_external_effect_reconciliations_effect_time',
        table_name='identity_account_external_effect_reconciliations',
    )
    op.drop_table('identity_account_external_effect_reconciliations')
