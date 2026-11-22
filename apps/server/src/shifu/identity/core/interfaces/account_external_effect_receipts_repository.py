from datetime import datetime
from typing import Protocol
from uuid import UUID

from shifu.identity.core.domain.structures.account_external_effect_receipt import (
    AccountExternalEffectReceiptAdmission,
    AccountExternalEffectReceiptReconciliation,
)


class AccountExternalEffectReceiptsRepository(Protocol):
    def admit(
        self, account_id: str, effect_id: UUID, operation: str
    ) -> AccountExternalEffectReceiptAdmission: ...

    def settle(self, account_id: str, effect_id: UUID) -> None: ...

    def mark_unknown(self, account_id: str, effect_id: UUID) -> None: ...

    def list_unresolved(
        self, limit: int
    ) -> tuple[AccountExternalEffectReceiptAdmission, ...]: ...

    def reconcile(
        self,
        reconciliation: AccountExternalEffectReceiptReconciliation,
        *,
        reconciled_at: datetime,
        stale_before: datetime,
    ) -> bool: ...

    def remove_reconciliations_before(self, cutoff: datetime, limit: int) -> int: ...

    def has_unresolved_for_account_id(self, account_id: str) -> bool: ...

    def remove_settled_for_account_id(self, account_id: str) -> int: ...
