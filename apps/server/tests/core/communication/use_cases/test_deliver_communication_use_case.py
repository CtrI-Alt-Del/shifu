from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import Communication, DeliveryAttempt
from shifu.communication.core.domain.enums import (
    CommunicationDeliveryState,
    CommunicationStatus,
    CommunicationType,
    CommunicationChannel,
    DeliveryAttemptStatus,
)
from shifu.communication.core.domain.events import (
    CommunicationDeliveryStateChangedEvent,
)
from shifu.communication.core.domain.structures import (
    DeliveryOutcome,
    EmailMessage,
    MessageContent,
    SecretEnvelope,
)
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
    EmailDeliveryProvider,
    MessageRenderer,
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
        self.id_provider.generate.return_value = '01JATTEMPT00000000000000001'
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.envelope_provider = create_autospec(
            SecretEnvelopeProvider,
            instance=True,
        )
        self.envelope_provider.decrypt.return_value = MessageContent(
            subject='Confirme seu e-mail',
            html='<p>Confirme</p>',
            text='Confirme',
        )
        self.renderer = create_autospec(MessageRenderer, instance=True)
        self.renderer.render.return_value = EmailMessage(
            idempotency_key='renderer-key',
            to='learner@example.com',
            subject='Confirme seu e-mail',
            html='<p>Confirme</p>',
            text='Confirme',
        )
        self.provider = create_autospec(EmailDeliveryProvider, instance=True)
        self.communication = Communication.create(
            id='01JCOMMUNICATION000000000000001',
            account_id='01JACCOUNT000000000000000001',
            type=CommunicationType.ACCOUNT_CONFIRMATION,
            channel=CommunicationChannel.EMAIL,
            recipient_email='learner@example.com',
            recipient_name='Pessoa Aprendente',
            content=None,
            status=CommunicationStatus.PENDING,
            idempotency_key='01JCOMMUNICATION000000000000001',
            created_at=self.now,
            updated_at=self.now,
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
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.side_effect = [
            None,
            self.attempt,
        ]
        self.subject = DeliverCommunicationUseCase(
            self.communication_database,
            self.id_provider,
            self.clock_provider,
            self.envelope_provider,
            self.renderer,
            self.provider,
        )

    def test_should_render_and_send_once_with_the_stable_communication_id(self) -> None:
        self.provider.send.return_value = DeliveryOutcome.accepted('provider-1')

        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.status is CommunicationStatus.SENT
        assert self.communication.attempt_count == 1
        assert self.attempt.status is DeliveryAttemptStatus.SUCCEEDED
        self.provider.send.assert_called_once_with(
            EmailMessage(
                idempotency_key=self.communication.id,
                to='learner@example.com',
                subject='Confirme seu e-mail',
                html='<p>Confirme</p>',
                text='Confirme',
            )
        )
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, CommunicationDeliveryStateChangedEvent)
        assert event.payload == event.payload.__class__(
            communication_id=self.communication.id,
            identity_confirmation_id=(
                self.communication.identity_confirmation_id or ''
            ),
            state=CommunicationDeliveryState.DELIVERED,
        )
        assert not hasattr(event.payload, 'account_id')
        assert not hasattr(event.payload, 'provider_message_id')

    def test_should_schedule_the_next_finite_retry_for_a_temporary_failure(
        self,
    ) -> None:
        self.provider.send.return_value = DeliveryOutcome.temporary_failure(
            'temporary_unavailable'
        )

        self.subject.execute(self.communication.id)

        assert self.communication.status is CommunicationStatus.PENDING
        assert self.communication.next_attempt_at == self.now + timedelta(minutes=1)
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.state is CommunicationDeliveryState.TEMPORARY_FAILURE

    def test_should_exhaust_the_fifth_attempt_without_another_provider_call(
        self,
    ) -> None:
        self.communication.attempt_count = 4
        self.attempt.attempt_number = 5
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.side_effect = [
            None,
            self.attempt,
        ]
        self.provider.send.return_value = DeliveryOutcome.temporary_failure(
            'temporary_unavailable'
        )

        self.subject.execute(self.communication.id)

        assert self.communication.status is CommunicationStatus.PERMANENTLY_FAILED
        assert self.communication.next_attempt_at is None
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.state is CommunicationDeliveryState.EXHAUSTED

    def test_should_stop_immediately_on_permanent_provider_rejection(self) -> None:
        self.provider.send.return_value = DeliveryOutcome.rejected()

        self.subject.execute(self.communication.id)

        assert self.communication.status is CommunicationStatus.REJECTED
        assert self.communication.next_attempt_at is None
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.state is CommunicationDeliveryState.PERMANENT_FAILURE

    def test_should_not_reprocess_a_terminal_request(self) -> None:
        self.communication.status = CommunicationStatus.SENT
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
        ]

        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        self.provider.send.assert_not_called()
        self.renderer.render.assert_not_called()
