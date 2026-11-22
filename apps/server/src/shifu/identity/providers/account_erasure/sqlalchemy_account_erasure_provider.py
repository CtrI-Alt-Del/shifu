from uuid import UUID

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.interfaces import ClockProvider


class SqlalchemyAccountErasureProvider:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._clock_provider = clock_provider

    def resolve_account_id(self, erasure_id: UUID) -> str | None:
        with self._identity_database.transaction() as repositories:
            return repositories.account_erasures.find_account_id(erasure_id)

    def acknowledge(self, erasure_id: UUID, participant: str) -> None:
        with self._identity_database.transaction() as repositories:
            repositories.account_erasures.acknowledge(
                erasure_id,
                participant,
                acknowledged_at=self._clock_provider.now(),
            )
