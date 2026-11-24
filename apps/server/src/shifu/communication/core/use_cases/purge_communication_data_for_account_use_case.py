from typing import ClassVar

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationQueuedEvent,
)
from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.shared.core.domain.structures import NonEmptyText


class PurgeCommunicationDataForAccountUseCase:
    """Delete account-owned communications, attempts, and outbox payloads."""

    _OUTBOX_EVENT_NAMES: ClassVar[tuple[str, ...]] = (
        CommunicationQueuedEvent.EVENT_NAME,
        CommunicationDeliveryStateChangedEvent.EVENT_NAME,
    )

    def __init__(self, communication_database: CommunicationDatabase) -> None:
        self._communication_database = communication_database

    def execute(self, account_id: str) -> None:
        account_id = NonEmptyText.create(
            account_id,
            error_type=InvalidCommunicationError,
        ).value

        with self._communication_database.transaction() as repositories:
            communication_ids = repositories.communications.find_ids_by_account_id(
                account_id
            )
            if not communication_ids:
                return

            for event_name in self._OUTBOX_EVENT_NAMES:
                repositories.events.remove_by_payload_values(
                    event_name,
                    'communication_id',
                    communication_ids,
                )
            repositories.delivery_attempts.remove_many_by_communication_ids(
                communication_ids
            )
            repositories.communications.remove_many_by_ids(communication_ids)
