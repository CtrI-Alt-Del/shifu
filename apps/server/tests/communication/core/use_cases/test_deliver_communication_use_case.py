from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec
from uuid import NAMESPACE_URL, uuid5

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
    DeliveryOutcome,
    MessageContent,
    SecretEnvelope,
)
from shifu.communication.core.interfaces import (
    CommunicationActivityProvider,
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
    EmailDeliveryProvider,
    MessageRendererProvider,
    SecretEnvelopeProvider,
)
from shifu.communication.core.use_cases import DeliverCommunicationUseCase
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    ClockProvider,
    IdentifierProvider,
)
from shifu.shared.core.domain.errors import AuthorizationError


class TestDeliverCommunicationUseCase:
    IDENTITY_ACTION_TOKEN_ID = '01JCONFIRMATION000000000000001'

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
        self.communication_activity_provider = create_autospec(
            CommunicationActivityProvider,
            instance=True,
        )
        self.communication_activity_provider.activity.return_value = nullcontext()
        self.account_activity_provider = create_autospec(
            AccountActivityProvider,
            instance=True,
        )
        self.account_activity_provider.external_effect.return_value = nullcontext(
            enter_result=True
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
            identity_action_token_id=self.IDENTITY_ACTION_TOKEN_ID,
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
        self.repositories.communications.find_account_id_by_id.return_value = (
            self.communication.account_id
        )
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.return_value = self.attempt
        self.subject = DeliverCommunicationUseCase(
            self.communication_database,
            self.id_provider,
            self.clock_provider,
            self.envelope_provider,
            self.renderer_provider,
            self.email_delivery_provider,
            self.communication_activity_provider,
            self.account_activity_provider,
        )

    def test_should_terminally_record_an_orphaned_processing_attempt_without_resending(
        self,
    ) -> None:
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
            self.communication,
        ]
        self.account_activity_provider.external_effect.return_value = nullcontext(
            enter_result=False
        )
        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.status is CommunicationStatus.PERMANENTLY_FAILED
        assert self.communication.failure_code == 'delivery_outcome_unknown'
        assert self.attempt.status is DeliveryAttemptStatus.FAILED
        assert self.attempt.failure_code == 'delivery_outcome_unknown'
        self.email_delivery_provider.send.assert_not_called()
        self.renderer_provider.render.assert_called_once()
        event = self.repositories.events.add.call_args.args[0]

        assert isinstance(event, CommunicationDeliveryStateChangedEvent)
        assert event.payload.state is CommunicationDeliveryState.PERMANENT_FAILURE

    def test_should_not_send_when_action_expires_after_preparation(self) -> None:
        self.communication.status = CommunicationStatus.PENDING
        self.communication.attempt_count = 0
        self.communication.expires_at = self.now + timedelta(seconds=1)
        self.clock_provider.now.side_effect = [
            self.now,
            self.communication.expires_at,
            self.communication.expires_at,
        ]
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.side_effect = [
            None,
            self.attempt,
        ]

        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.status is CommunicationStatus.REJECTED
        assert self.communication.failure_code == 'action_expired'
        assert self.attempt.status is DeliveryAttemptStatus.FAILED
        self.email_delivery_provider.send.assert_not_called()
        event = self.repositories.events.add.call_args.args[0]

        assert isinstance(event, CommunicationDeliveryStateChangedEvent)
        assert event.payload.state is CommunicationDeliveryState.EXPIRED

    def test_should_not_settle_or_send_when_account_activity_is_denied(self) -> None:
        self.communication_activity_provider.activity.side_effect = AuthorizationError

        result = self.subject.execute(self.communication.id)

        assert result is None
        self.repositories.communications.find_by_id.assert_called_once_with(
            self.communication.id
        )
        self.repositories.delivery_attempts.add.assert_not_called()
        self.repositories.delivery_attempts.update.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.email_delivery_provider.send.assert_not_called()
        self.renderer_provider.render.assert_not_called()

    def test_should_hold_receipt_barrier_only_after_prepare_transaction_closes(
        self,
    ) -> None:
        self.communication.status = CommunicationStatus.PENDING
        self.communication.attempt_count = 0
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.side_effect = [
            None,
            self.attempt,
        ]
        self.email_delivery_provider.send.return_value = DeliveryOutcome.accepted(
            'provider-message'
        )

        def send_without_open_database_transaction(
            message: EmailMessage,
        ) -> DeliveryOutcome:
            assert (
                self.communication_database.transaction.return_value.__enter__.call_count
                == self.communication_database.transaction.return_value.__exit__.call_count
            )
            return DeliveryOutcome.accepted('provider-message')

        self.email_delivery_provider.send.side_effect = (
            send_without_open_database_transaction
        )

        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.status is CommunicationStatus.SENT
        effect_id = uuid5(
            NAMESPACE_URL,
            f'shifu.communication.email.send:{self.communication.id}:1',
        )
        self.account_activity_provider.external_effect.assert_called_once_with(
            self.communication.account_id,
            effect_id,
            'communication.email.send',
            allow_pending_confirmation=True,
        )
        self.communication_activity_provider.activity.assert_called_once_with(
            self.communication.account_id
        )
        self.email_delivery_provider.send.assert_called_once()

    def test_should_not_send_when_external_effect_activity_is_denied(self) -> None:
        self.communication.status = CommunicationStatus.PENDING
        self.communication.attempt_count = 0
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.return_value = None
        self.account_activity_provider.external_effect.side_effect = AuthorizationError

        result = self.subject.execute(self.communication.id)

        assert result is None
        assert self.repositories.communications.find_by_id.call_count == 3
        self.repositories.delivery_attempts.add.assert_called_once()
        self.email_delivery_provider.send.assert_not_called()

    def test_should_not_resend_when_external_effect_receipt_is_already_settled(
        self,
    ) -> None:
        self.communication.status = CommunicationStatus.PENDING
        self.communication.attempt_count = 0
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.side_effect = [
            None,
            self.attempt,
        ]
        self.account_activity_provider.external_effect.return_value = nullcontext(
            enter_result=False
        )

        result = self.subject.execute(self.communication.id)

        assert result is self.communication
        assert self.communication.failure_code == 'delivery_outcome_unknown'
        self.email_delivery_provider.send.assert_not_called()

    def test_should_not_open_receipt_when_local_attempt_preparation_fails(self) -> None:
        self.communication.status = CommunicationStatus.PENDING
        self.communication.attempt_count = 0
        self.repositories.communications.find_by_id.side_effect = [
            self.communication,
            self.communication,
            self.communication,
        ]
        self.repositories.delivery_attempts.find_by_communication_id_and_attempt_number.return_value = None
        self.repositories.delivery_attempts.add.side_effect = RuntimeError(
            'local preparation failed'
        )

        with pytest.raises(RuntimeError, match='local preparation failed'):
            self.subject.execute(self.communication.id)

        self.account_activity_provider.external_effect.assert_not_called()
        self.email_delivery_provider.send.assert_not_called()
