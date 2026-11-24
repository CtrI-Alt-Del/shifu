from datetime import timedelta
from re import fullmatch

from shifu.identity.core.domain.errors import ExternalEffectReceiptReconciliationError
from shifu.identity.core.domain.structures import (
    AccountExternalEffectReceiptReconciliation,
)
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.interfaces import ClockProvider


class ReconcileAccountExternalEffectReceiptUseCase:
    STALE_RECEIPT_AFTER = timedelta(minutes=30)
    _OPERATOR_ID_PATTERN = r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}'
    _EVIDENCE_REFERENCE_PATTERN = r'[A-Z0-9][A-Z0-9._-]{0,159}'
    _EVIDENCE_SHA256_PATTERN = r'[0-9a-f]{64}'
    _OPERATION_PATTERN = r'[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*'

    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def execute(
        self, reconciliation: AccountExternalEffectReceiptReconciliation
    ) -> None:
        if not self._is_valid(reconciliation):
            raise ExternalEffectReceiptReconciliationError

        now = self._clock_provider.now()
        with self._identity_database.transaction() as repositories:
            reconciled = repositories.external_effect_receipts.reconcile(
                reconciliation,
                reconciled_at=now,
                stale_before=now - self.STALE_RECEIPT_AFTER,
            )
            if not reconciled:
                raise ExternalEffectReceiptReconciliationError

    @classmethod
    def _is_valid(
        cls, reconciliation: AccountExternalEffectReceiptReconciliation
    ) -> bool:
        return bool(
            reconciliation.account_id
            and fullmatch(cls._OPERATION_PATTERN, reconciliation.operation)
            and reconciliation.resolution in ('applied', 'not_applied')
            and reconciliation.confirm_no_live_operation
            and fullmatch(cls._OPERATOR_ID_PATTERN, reconciliation.operator_id)
            and fullmatch(
                cls._EVIDENCE_REFERENCE_PATTERN, reconciliation.evidence_reference
            )
            and fullmatch(cls._EVIDENCE_SHA256_PATTERN, reconciliation.evidence_sha256)
        )
