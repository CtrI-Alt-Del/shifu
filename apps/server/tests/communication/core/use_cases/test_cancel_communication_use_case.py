from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationCancellationReason,
    CommunicationChannel,
    CommunicationDeliveryState,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
)
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import MessageContent, SecretEnvelope
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import CancelCommunicationUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestCancelCommunicationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.communication_database = create_autospec(
            CommunicationDatabase,
            instance=True,
        )
        self.repositories = create_autospec(
            CommunicationDatabaseRepositories,
            instance=True,
        )
        self.communication_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 8, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.communication = Communication.create(
            id='01JCOMMUNICATION000000000000001',
            account_id='01JACCOUNT000000000000000001',
            type=CommunicationType.ACCOUNT_CONFIRMATION,
            channel=CommunicationChannel.EMAIL,
            recipient_email='learner@example.com',
            recipient_name='Pessoa Aprendente',
            content=MessageContent(
                subject='Confirme seu e-mail',
                html='<p>Confirme</p>',
                text='Confirme',
            ),
            status=CommunicationStatus.PENDING,
            idempotency_key='01JCOMMUNICATION000000000000001',
            created_at=self.now,
            updated_at=self.now,
            identity_confirmation_id='01JCONFIRMATION000000000000001',
            encrypted_content=SecretEnvelope(ciphertext='encrypted-content'),
        )
        self.repositories.communications.find_by_id.return_value = self.communication
        self.subject = CancelCommunicationUseCase(
            self.communication_database,
            self.clock_provider,
        )

    def test_should_cancel_pending_delivery_for_confirmation_without_redacting_it(
        self,
    ) -> None:
        cancelled = self.subject.execute(
            self.communication.id,
            self.communication.identity_confirmation_id or '',
            CommunicationCancellationReason.CONFIRMED,
        )

        assert cancelled is True
        assert self.communication.status is CommunicationStatus.CANCELLED
        assert self.communication.account_id is not None
        assert self.communication.recipient_email == 'learner@example.com'
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, CommunicationDeliveryStateChangedEvent)
        assert event.payload.state is CommunicationDeliveryState.CANCELLED
        assert event.payload.identity_confirmation_id == (
            '01JCONFIRMATION000000000000001'
        )

    def test_should_redact_every_active_association_when_expired(self) -> None:
        cancelled = self.subject.execute(
            self.communication.id,
            self.communication.identity_confirmation_id or '',
            'expired',
        )

        assert cancelled is True
        assert self.communication.status is CommunicationStatus.CANCELLED
        assert self.communication.account_id is None
        assert self.communication.recipient_email is None
        assert self.communication.recipient_name is None
        assert self.communication.identity_confirmation_id is None
        assert self.communication.content is None
        assert self.communication.encrypted_content is None
        assert self.communication.is_redacted

    def test_should_redact_delivered_rows_without_reopening_or_cancelling_state(
        self,
    ) -> None:
        self.communication.status = CommunicationStatus.SENT
        self.communication.provider_message_id = 'provider-1'

        cancelled = self.subject.execute(
            self.communication.id,
            self.communication.identity_confirmation_id or '',
            CommunicationCancellationReason.EXPIRED,
        )

        assert cancelled is True
        assert self.communication.status is CommunicationStatus.SENT
        assert self.communication.is_redacted
        self.repositories.events.add.assert_not_called()

    def test_should_ignore_duplicate_or_mismatched_cancellation(self) -> None:
        first = self.subject.execute(
            self.communication.id,
            self.communication.identity_confirmation_id or '',
            CommunicationCancellationReason.REISSUED,
        )
        updates = self.repositories.communications.update.call_count

        second = self.subject.execute(
            self.communication.id,
            '01JOTHERCONFIRMATION00000000000001',
            CommunicationCancellationReason.REISSUED,
        )

        assert first is True
        assert second is False
        assert self.repositories.communications.update.call_count == updates
        assert self.repositories.events.add.call_count == 1

    def test_should_reject_an_unknown_cancellation_reason_without_transaction(
        self,
    ) -> None:
        with pytest.raises(InvalidCommunicationError):
            self.subject.execute(
                self.communication.id,
                self.communication.identity_confirmation_id or '',
                'unknown',
            )

        self.communication_database.transaction.assert_not_called()
