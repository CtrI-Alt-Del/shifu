from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
    CommunicationQueuedEvent,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import (
    PurgeCommunicationDataForAccountUseCase,
)


class TestPurgeCommunicationDataForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(CommunicationDatabase, instance=True)
        self.repositories = create_autospec(
            CommunicationDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.subject = PurgeCommunicationDataForAccountUseCase(self.database)

    def test_should_remove_account_messages_attempts_and_outbox_events(self) -> None:
        communication_ids = {'01JCOMMUNICATION000000000000001'}
        self.repositories.communications.find_ids_by_account_id.return_value = (
            communication_ids
        )

        self.subject.execute('01JACCOUNT000000000000000001')

        self.repositories.events.remove_by_payload_values.assert_any_call(
            CommunicationQueuedEvent.EVENT_NAME,
            'communication_id',
            communication_ids,
        )
        self.repositories.events.remove_by_payload_values.assert_any_call(
            CommunicationDeliveryStateChangedEvent.EVENT_NAME,
            'communication_id',
            communication_ids,
        )
        self.repositories.delivery_attempts.remove_many_by_communication_ids.assert_called_once_with(
            communication_ids
        )
        self.repositories.communications.remove_many_by_ids.assert_called_once_with(
            communication_ids
        )

    def test_should_leave_unrelated_datasets_untouched_when_account_has_no_messages(
        self,
    ) -> None:
        self.repositories.communications.find_ids_by_account_id.return_value = set()

        self.subject.execute('01JACCOUNT000000000000000001')

        self.repositories.events.remove_by_payload_values.assert_not_called()
        self.repositories.delivery_attempts.remove_many_by_communication_ids.assert_not_called()
        self.repositories.communications.remove_many_by_ids.assert_not_called()

    @pytest.mark.parametrize('account_id', ['', '   '])
    def test_should_reject_empty_account_id(self, account_id: str) -> None:
        with pytest.raises(InvalidCommunicationError):
            self.subject.execute(account_id)

        self.database.transaction.assert_not_called()
