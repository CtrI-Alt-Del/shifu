from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountConfirmationResultStatus,
    AccountStatus,
)
from shifu.identity.core.domain.events import (
    AccountActivatedEvent,
    AccountConfirmationCancelledEvent,
)
from shifu.identity.core.domain.structures import AccountConfirmationResult
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.identity.core.use_cases.confirm_account_use_case import (
    ConfirmAccountUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider


class TestConfirmAccountUseCase:
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
        self.action_token_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.action_token_provider.hash.return_value = 'token-hash'
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.subject = ConfirmAccountUseCase(
            self.identity_database,
            self.clock_provider,
            self.action_token_provider,
        )

    def test_should_activate_once_and_cancel_all_confirmation_deliveries(self) -> None:
        account = AccountFaker.fake(
            id='01JACCOUNT000000000000000001',
            status=AccountStatus.PENDING_CONFIRMATION,
            email='learner@example.com',
            access_version=3,
            created_at=self.now - timedelta(hours=1),
            updated_at=self.now - timedelta(hours=1),
            confirmed_at=None,
        )
        current_token = AccountActionToken(
            id='01JCONFIRM00000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='token-hash',  # noqa: S106
            issued_at=self.now - timedelta(minutes=5),
            expires_at=self.now + timedelta(hours=23),
            updated_at=self.now - timedelta(minutes=5),
            communication_id='01JCOMMUNICATION000000000001',
        )
        sibling_token = AccountActionToken(
            id='01JSIBLING00000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='sibling-hash',  # noqa: S106
            issued_at=self.now - timedelta(hours=1),
            expires_at=self.now + timedelta(hours=23),
            updated_at=self.now - timedelta(hours=1),
            communication_id='01JSIBLINGCOMMUNICATION000001',
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = (
            current_token
        )
        self.repositories.accounts.find_by_id.return_value = account
        self.repositories.account_action_tokens.find_many_by_account_id_and_type.return_value = [
            current_token,
            sibling_token,
        ]

        result = self.subject.execute('raw-confirmation-token')

        assert result.result is AccountConfirmationResultStatus.ACTIVATED
        assert result.profile is not None
        assert result.profile.account_id == account.id
        assert result.profile.email == 'learner@example.com'
        assert result.profile.status is AccountStatus.ACTIVE
        assert result.access_version == 4
        assert account.status is AccountStatus.ACTIVE
        assert account.access_version == 4
        assert account.confirmed_at == self.now
        assert current_token.status is AccountActionTokenStatus.USED
        assert sibling_token.status is AccountActionTokenStatus.INVALIDATED
        assert self.repositories.accounts.update.call_args.args[0] is account
        assert self.repositories.account_action_tokens.update.call_count == 2

        events = [call.args[0] for call in self.repositories.events.add.call_args_list]
        cancellation_events = [
            event
            for event in events
            if isinstance(event, AccountConfirmationCancelledEvent)
        ]
        assert {event.payload.communication_id for event in cancellation_events} == {
            current_token.communication_id,
            sibling_token.communication_id,
        }
        activated_event = next(
            event for event in events if isinstance(event, AccountActivatedEvent)
        )
        assert activated_event.payload.account_id == account.id
        assert activated_event.payload.activated_at == self.now.isoformat()
        self.action_token_provider.hash.assert_called_once_with(
            'raw-confirmation-token'
        )

    def test_should_commit_expired_token_without_activating_account(self) -> None:
        account = AccountFaker.fake(
            status=AccountStatus.PENDING_CONFIRMATION,
            created_at=self.now - timedelta(days=1),
            updated_at=self.now - timedelta(days=1),
            confirmed_at=None,
        )
        token = AccountActionToken(
            id='01JCONFIRM00000000000000001',
            account_id=account.id,
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=AccountActionTokenStatus.PENDING,
            token_hash='token-hash',  # noqa: S106
            issued_at=self.now - timedelta(hours=24),
            expires_at=self.now,
            updated_at=self.now - timedelta(hours=24),
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = token
        self.repositories.accounts.find_by_id.return_value = account

        result = self.subject.execute('expired-token')

        assert result == AccountConfirmationResult(
            result=AccountConfirmationResultStatus.EXPIRED
        )
        assert token.status is AccountActionTokenStatus.EXPIRED
        assert token.updated_at == self.now
        assert account.status is AccountStatus.PENDING_CONFIRMATION
        self.repositories.account_action_tokens.update.assert_called_once_with(token)
        self.repositories.accounts.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        ('status', 'expected_result'),
        [
            (AccountActionTokenStatus.USED, AccountConfirmationResultStatus.USED),
            (
                AccountActionTokenStatus.INVALIDATED,
                AccountConfirmationResultStatus.INVALID,
            ),
            (AccountActionTokenStatus.EXPIRED, AccountConfirmationResultStatus.EXPIRED),
        ],
    )
    def test_should_map_non_pending_token_to_safe_result(
        self,
        status: AccountActionTokenStatus,
        expected_result: AccountConfirmationResultStatus,
    ) -> None:
        token = AccountActionToken(
            id='01JCONFIRM00000000000000001',
            account_id='01JACCOUNT000000000000000001',
            type=AccountActionTokenType.EMAIL_CONFIRMATION,
            status=status,
            token_hash='token-hash',  # noqa: S106
            issued_at=self.now - timedelta(hours=24),
            expires_at=self.now - timedelta(minutes=1),
            updated_at=self.now - timedelta(minutes=1),
        )
        self.repositories.account_action_tokens.find_by_hash.return_value = token

        result = self.subject.execute('non-pending-token')

        assert result.result is expected_result
        self.repositories.accounts.find_by_id.assert_not_called()
        self.repositories.account_action_tokens.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_return_invalid_without_account_or_token_side_effects(self) -> None:
        self.repositories.account_action_tokens.find_by_hash.return_value = None

        result = self.subject.execute('unknown-token')

        assert result.result is AccountConfirmationResultStatus.INVALID
        self.repositories.accounts.find_by_id.assert_not_called()
        self.repositories.events.add.assert_not_called()
