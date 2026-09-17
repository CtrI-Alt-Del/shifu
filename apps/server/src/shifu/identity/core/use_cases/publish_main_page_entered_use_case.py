from shifu.identity.core.domain.events import (
    MainPageEnteredEvent,
    MainPageEnteredPayload,
)
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class PublishMainPageEnteredUseCase:
    def __init__(
        self,
        identity_database: IdentityDatabase,
        id_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._identity_database = identity_database
        self._id_provider = id_provider
        self._clock_provider = clock_provider

    def execute(self, account_id: str) -> None:
        occurred_at = self._clock_provider.now().isoformat()
        event = MainPageEnteredEvent(
            payload=MainPageEnteredPayload(
                event_id=self._id_provider.generate(),
                account_id=account_id,
                occurred_at=occurred_at,
            )
        )

        with self._identity_database.transaction() as repositories:
            repositories.events.add(event)
