from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import Communication, DeliveryAttempt
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationDeliveryState,
    CommunicationStatus,
    CommunicationType,
    DeliveryAttemptStatus,
)
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
)
from shifu.communication.core.domain.structures import (
    EmailMessage,
    MessageContent,
    SecretEnvelope,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
    EmailDeliveryProvider,
    MessageRendererProvider,
    SecretEnvelopeProvider,
)
from shifu.communication.core.use_cases import DeliverCommunicationUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestDeliverCommunicationUseCase:
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
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.envelope_provider = create_autospec(
            SecretEnvelopeProvider,
            instance=True,
        )
        self.renderer_provider = create_autospec(
            MessageRendererProvider,
            instance=True,
        )
        self.renderer_provider.render.return_value = EmailMessage(
            idempotency_key='renderer-key',
            to='learner@example.com',
            subject='Confirme seu e-mail',
            html='<p>Confirme</p>',
            text='Confirme',
        )
        self.email_delivery_provider = create_autospec(
            EmailDeliveryProvider,
            instance=True,
        )
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
            status=CommunicationStatus.PROCESSING,
            idempotency_key='01JCOMMUNICATION000000000000001',
            created_at=self.now,
            updated_at=self.now,
            attempt_count=1,
            identity_confirmation_id='01JCONFIRMATION000000000000001',
            encrypted_content=SecretEnvelope(ciphertext='encrypted-content'),
        )
        self.attempt = DeliveryAttempt.create(
            id='01JATTEMPT00000000000000001',
            communication_id=self.communication.id,
            attempt_number=1,
            attempted_at=self.now,
        )
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.return_value = self.attempt
        self.subject = DeliverCommunicationUseCase(
            self.communication_database,
            self.id_provider,
            self.clock_provider,
            self.envelope_provider,
            self.renderer_provider,
            self.email_delivery_provider,
        )

    def test_should_terminally_record_an_orphaned_processing_attempt_without_resending(
        self,
    ) -> None:
        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.status is CommunicationStatus.PERMANENTLY_FAILED
        assert self.communication.failure_code == 'delivery_outcome_unknown'
        assert self.attempt.status is DeliveryAttemptStatus.FAILED
        assert self.attempt.failure_code == 'delivery_outcome_unknown'
        self.email_delivery_provider.send.assert_not_called()
        self.renderer_provider.render.assert_not_called()
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, CommunicationDeliveryStateChangedEvent)
        assert event.payload.state is CommunicationDeliveryState.PERMANENT_FAILURE
