from shifu.identity.core.domain.errors import ExternalEffectReceiptReconciliationError
from shifu.identity.core.domain.structures import AccountExternalEffectReceiptAdmission
from shifu.identity.core.interfaces import IdentityDatabase


class ListUnresolvedAccountExternalEffectReceiptsUseCase:
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 1000

    def __init__(self, identity_database: IdentityDatabase) -> None:
        self._identity_database = identity_database

    def execute(
        self, limit: int = DEFAULT_LIMIT
    ) -> tuple[AccountExternalEffectReceiptAdmission, ...]:
        if not 1 <= limit <= self.MAX_LIMIT:
            raise ExternalEffectReceiptReconciliationError

        with self._identity_database.transaction() as repositories:
            return repositories.external_effect_receipts.list_unresolved(limit)
