from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class AccountExternalEffectReconciliationModel(Model):
    __tablename__ = 'identity_account_external_effect_reconciliations'
    __table_args__ = (
        CheckConstraint(
            "previous_state IN ('in_flight', 'unknown')",
            name='ck_identity_external_effect_reconciliations_previous_state',
        ),
        CheckConstraint(
            "resolution IN ('applied', 'not_applied')",
            name='ck_identity_external_effect_reconciliations_resolution',
        ),
        CheckConstraint(
            'length(trim(operation)) BETWEEN 1 AND 120',
            name='ck_identity_external_effect_reconciliations_operation',
        ),
        CheckConstraint(
            'length(trim(operator_id)) BETWEEN 1 AND 64',
            name='ck_identity_external_effect_reconciliations_operator',
        ),
        CheckConstraint(
            'length(trim(evidence_reference)) BETWEEN 1 AND 160',
            name='ck_identity_external_effect_reconciliations_evidence_reference',
        ),
        CheckConstraint(
            'length(evidence_sha256) = 64',
            name='ck_identity_external_effect_reconciliations_evidence_sha256',
        ),
        Index(
            'ix_identity_external_effect_reconciliations_effect_time',
            'effect_id',
            'reconciled_at',
        ),
        Index('ix_identity_external_effect_reconciliations_time', 'reconciled_at'),
    )

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    effect_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(16), nullable=False)
    resolution: Mapped[str] = mapped_column(String(16), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reconciled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
