from uuid import UUID

from shifu.identity.core.domain.structures import AccountErasureResult
from shifu.identity.core.interfaces import IdentityDatabase


class GetAccountErasureStatusUseCase:
    def __init__(self, identity_database: IdentityDatabase) -> None:
        self._identity_database = identity_database

    def execute(self, erasure_id: UUID) -> AccountErasureResult | None:
        with self._identity_database.transaction() as repositories:
            return repositories.account_erasures.find_result(erasure_id)
