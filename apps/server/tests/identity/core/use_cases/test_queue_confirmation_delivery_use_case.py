from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    ConfirmationDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ConfirmationDeliveryGateway,
    ConfirmationDeliveryRequest,
    ConfirmationDeliveryResult,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases import QueueConfirmationDeliveryUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestQueueConfirmationDeliveryUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(
            IdentityDatabaseRepositories,
            instance=True,
        )
        self.identity_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.gateway = create_autospec(ConfirmationDeliveryGateway, instance=True)
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.request = ConfirmationDeliveryRequest(
            communication_id='01JCOMMUNICATION000000000001',
            identity_action_token_id='01JTOKEN0000000000000000001',  # noqa: S106
            account_id='01JACCOUNT000000000000000001',
            recipient_email='learner@example.com',
            recipient_name='Pessoa Aprendente',
            confirmation_token='confirmation-token',  # noqa: S106
            expires_at=self.now + timedelta(hours=24),
        )
        self.token = AccountActionToken(
            id=self.request.identity_action_token_id,
            account_id=self.request.account_id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='token-hash',  # noqa: S106
            issued_at=self.now,
            expires_at=self.now + timedelta(hours=24),
            updated_at=self.now,
            communication_id=self.request.communication_id,
        )
        self.subject = QueueConfirmationDeliveryUseCase(
            identity_database=self.identity_database,
            clock_provider=self.clock_provider,
            delivery_gateway=self.gateway,
        )

    def test_should_not_touch_persistence_when_delivery_is_queued(self) -> None:
        self.gateway.queue.return_value = ConfirmationDeliveryResult(
            status=ConfirmationDeliveryQueueStatus.QUEUED
        )

        self.subject.execute(self.request)

        self.gateway.queue.assert_called_once_with(self.request)
        self.identity_database.transaction.assert_not_called()

    def test_should_record_delivery_unavailable_on_the_token(self) -> None:
        self.gateway.queue.return_value = ConfirmationDeliveryResult(
            status=ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
        )
        tokens = self.repositories.account_action_tokens
        tokens.find_by_id.return_value = self.token
        recorded_at = self.now + timedelta(seconds=2)
        self.clock_provider.now.return_value = recorded_at

        self.subject.execute(self.request)

        tokens.find_by_id.assert_called_once_with(self.request.identity_action_token_id)
        assert (
            self.token.delivery_status
            is AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE
        )
        assert self.token.updated_at == recorded_at
        tokens.update.assert_called_once_with(self.token)

    def test_should_ignore_a_missing_token_when_recording_delivery_unavailable(
        self,
    ) -> None:
        self.gateway.queue.return_value = ConfirmationDeliveryResult(
            status=ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
        )
        tokens = self.repositories.account_action_tokens
        tokens.find_by_id.return_value = None

        self.subject.execute(self.request)

        tokens.update.assert_not_called()

    def test_should_not_rewrite_a_token_that_already_has_a_final_delivery_state(
        self,
    ) -> None:
        self.gateway.queue.return_value = ConfirmationDeliveryResult(
            status=ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
        )
        self.token.delivery_status = AccountActionTokenDeliveryStatus.DELIVERED
        tokens = self.repositories.account_action_tokens
        tokens.find_by_id.return_value = self.token

        self.subject.execute(self.request)

        assert self.token.delivery_status is AccountActionTokenDeliveryStatus.DELIVERED
        tokens.update.assert_not_called()

    def test_should_propagate_gateway_failures_without_recording_state(self) -> None:
        self.gateway.queue.side_effect = RuntimeError('gateway down')

        with pytest.raises(RuntimeError):
            self.subject.execute(self.request)

        self.identity_database.transaction.assert_not_called()
