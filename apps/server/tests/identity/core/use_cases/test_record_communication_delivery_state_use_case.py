from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationDeliveryStatus,
)
from shifu.identity.core.domain.errors import AccountConfirmationNotAllowedError
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.record_communication_delivery_state_use_case import (
    RecordCommunicationDeliveryStateUseCase,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.interfaces import ClockProvider


class TestRecordCommunicationDeliveryStateUseCase:
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
        self.recorded_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.recorded_at
        self.token = AccountActionToken(
            id='01JCONFIRM00000000000000001',
            account_id='01JACCOUNT000000000000000001',
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='token-hash',  # noqa: S106
            issued_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            expires_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            communication_id='01JCOMMUNICATION000000000001',
        )
        self.repositories.account_action_tokens.find_by_id.return_value = self.token
        self.subject = RecordCommunicationDeliveryStateUseCase(
            self.identity_database,
            self.clock_provider,
        )

    def test_should_record_matching_delivery_state_once(self) -> None:
        recorded = self.subject.execute(
            '01JCOMMUNICATION000000000001',
            self.token.id,
            AccountConfirmationDeliveryStatus.DELIVERED,
        )

        assert recorded is True
        assert self.token.delivery_status is AccountConfirmationDeliveryStatus.DELIVERED
        assert self.token.updated_at == self.recorded_at
        self.repositories.account_action_tokens.update.assert_called_once_with(
            self.token
        )

        replayed = self.subject.execute(
            '01JCOMMUNICATION000000000001',
            self.token.id,
            AccountConfirmationDeliveryStatus.DELIVERED,
        )

        assert replayed is False
        assert self.repositories.account_action_tokens.update.call_count == 1

    def test_should_allow_temporary_failure_to_resolve_to_delivery(self) -> None:
        self.token.delivery_status = AccountConfirmationDeliveryStatus.TEMPORARY_FAILURE

        recorded = self.subject.execute(
            '01JCOMMUNICATION000000000001',
            self.token.id,
            AccountConfirmationDeliveryStatus.DELIVERED,
        )

        assert recorded is True
        assert self.token.delivery_status is AccountConfirmationDeliveryStatus.DELIVERED

    def test_should_ignore_mismatched_correlation_without_mutation(self) -> None:
        recorded = self.subject.execute(
            'different-communication',
            self.token.id,
            AccountConfirmationDeliveryStatus.DELIVERED,
        )

        assert recorded is False
        assert self.token.delivery_status is None
        self.repositories.account_action_tokens.update.assert_not_called()
        self.clock_provider.now.assert_not_called()

    def test_should_reject_unvalidated_delivery_state(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                '01JCOMMUNICATION000000000001',
                self.token.id,
                'not-a-state',  # type: ignore[arg-type]
            )

        self.identity_database.transaction.assert_not_called()

    def test_should_reject_delivery_state_for_non_confirmation_token(self) -> None:
        self.token.type = AccountActionTokenType.PASSWORD_RECOVERY

        with pytest.raises(AccountConfirmationNotAllowedError):
            self.subject.execute(
                '01JCOMMUNICATION000000000001',
                self.token.id,
                AccountConfirmationDeliveryStatus.DELIVERED,
            )

        self.repositories.account_action_tokens.update.assert_not_called()
