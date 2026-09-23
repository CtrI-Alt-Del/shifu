from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.events import CommunicationQueuedEvent
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.communication.core.domain.structures import (
    CommunicationRequest,
    MessageContent,
    SecretEnvelope,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
    SecretEnvelopeProvider,
)
from shifu.communication.core.use_cases import QueueCommunicationUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestQueueCommunicationUseCase:
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
        self.repositories.communications.find_by_id.return_value = None
        self.repositories.communications.find_by_idempotency_key.return_value = None
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.envelope_provider = create_autospec(
            SecretEnvelopeProvider,
            instance=True,
        )
        self.created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.created_at
        self.envelope_provider.encrypt.return_value = SecretEnvelope(
            ciphertext='encrypted-content',
            key_id='current',
        )
        self.subject = QueueCommunicationUseCase(
            self.communication_database,
            self.id_provider,
            self.clock_provider,
            self.envelope_provider,
        )
        self.request = CommunicationRequest(
            communication_id='01JCOMMUNICATION000000000000001',
            identity_confirmation_id='01JCONFIRMATION000000000000001',
            account_id='01JACCOUNT000000000000000001',
            type=CommunicationType.ACCOUNT_CONFIRMATION,
            channel=CommunicationChannel.EMAIL,
            recipient_email=' Learner@Example.com ',
            recipient_name='Pessoa Aprendente',
            content=MessageContent(
                subject='Confirme seu e-mail',
                html='<p>Confirme</p>',
                text='Confirme',
            ),
        )

    def test_should_persist_preassigned_identity_and_id_only_queue_event(self) -> None:
        result = self.subject.execute(self.request)

        assert result.id == self.request.communication_id
        assert result.identity_confirmation_id == (
            self.request.identity_confirmation_id
        )
        assert result.status is CommunicationStatus.PENDING
        assert result.recipient_email == 'learner@example.com'
        assert result.content is None
        assert result.encrypted_content == self.envelope_provider.encrypt.return_value
        self.envelope_provider.encrypt.assert_called_once_with(self.request.content)
        self.repositories.communications.add.assert_called_once_with(result)

        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, CommunicationQueuedEvent)
        assert event.payload.communication_id == result.id
        assert not hasattr(event.payload, 'account_id')
        assert not hasattr(event.payload, 'recipient_email')

    def test_should_return_existing_request_without_reencrypting_or_republishing(
        self,
    ) -> None:
        existing = Communication.create(
            id=self.request.communication_id,
            account_id=self.request.account_id,
            type=self.request.type,
            channel=self.request.channel,
            recipient_email=self.request.recipient_email,
            recipient_name=self.request.recipient_name,
            content=None,
            status=CommunicationStatus.PENDING,
            idempotency_key=self.request.idempotency_key,
            created_at=self.created_at,
            updated_at=self.created_at,
            identity_confirmation_id=self.request.identity_confirmation_id,
            encrypted_content=self.envelope_provider.encrypt.return_value,
        )
        self.repositories.communications.find_by_id.return_value = existing

        result = self.subject.execute(self.request)

        assert result is existing
        self.envelope_provider.encrypt.assert_not_called()
        self.repositories.communications.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.clock_provider.now.assert_not_called()

    def test_should_reject_an_uncontrolled_message_type_before_transaction(
        self,
    ) -> None:
        with pytest.raises(InvalidCommunicationError):
            CommunicationRequest(
                communication_id=self.request.communication_id,
                identity_confirmation_id=self.request.identity_confirmation_id,
                account_id=self.request.account_id,
                type='marketing',  # type: ignore[arg-type]
                channel=CommunicationChannel.EMAIL,
                recipient_email=self.request.recipient_email,
                recipient_name=self.request.recipient_name,
                content=self.request.content,
            )

        self.communication_database.transaction.assert_not_called()
