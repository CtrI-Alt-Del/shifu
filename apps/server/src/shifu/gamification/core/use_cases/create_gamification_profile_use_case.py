from datetime import datetime

from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.shared.core.interfaces import IdentifierProvider


class CreateGamificationProfileUseCase:
    """Idempotently create the account's Gamification profile on activation."""

    def __init__(
        self,
        database: GamificationDatabase,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider

    def execute(self, account_id: str, *, now: datetime) -> None:
        with self._database.transaction() as repositories:
            existing = repositories.profiles.find_by_account_id(account_id)
            if existing is not None:
                return
            repositories.profiles.add(
                GamificationProfile.create(
                    id=self._identifier_provider.generate(),
                    account_id=account_id,
                    created_at=now,
                )
            )
