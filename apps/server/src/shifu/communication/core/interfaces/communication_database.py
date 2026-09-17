from contextlib import AbstractContextManager
from typing import Protocol

from shifu.communication.core.interfaces.communications_repository import (
    CommunicationsRepository,
)
from shifu.communication.core.interfaces.delivery_attempts_repository import (
    DeliveryAttemptsRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class CommunicationDatabaseRepositories:
    communications: CommunicationsRepository
    delivery_attempts: DeliveryAttemptsRepository
    events: EventsRepository


class CommunicationDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[CommunicationDatabaseRepositories]:
        """Open the transaction boundary for one Communication operation."""
        ...
