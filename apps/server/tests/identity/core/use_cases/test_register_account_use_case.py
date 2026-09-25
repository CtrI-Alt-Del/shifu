from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import (
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidPasswordError,
)
from shifu.identity.core.domain.structures import AccountRegistration
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    IdentityDatabaseRepositories,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases.register_account_use_case import (
    RegisterAccountUseCase,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider

if TYPE_CHECKING:
    from shifu.identity.core.domain.events import AccountCreatedEvent


class TestRegisterAccountUseCase:
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
        self.repositories.accounts.find_non_deleted_by_email.return_value = None
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.clock_provider = create_autospec(ClockProvider, instance=True)
        self.password_hashing_provider = create_autospec(
            PasswordHashingProvider,
            instance=True,
        )
        self.action_token_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.pending_handle_provider = create_autospec(
            ActionTokenProvider,
            instance=True,
        )
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self.clock_provider.now.return_value = self.now
        self.id_provider.generate.side_effect = [
            '01JACCOUNT000000000000000001',
            '01JCONFIRM00000000000000001',
            '01JCOMMUNICATION000000000001',
        ]
        self.action_token_provider.generate.return_value = 'confirmation-token'
        self.action_token_provider.hash.return_value = 'confirmation-token-hash'
        self.pending_handle_provider.generate.return_value = 'pending-handle'
        self.pending_handle_provider.hash.return_value = 'pending-handle-hash'
        self.password_hashing_provider.hash.return_value = 'argon2id-hash'
        self.subject = RegisterAccountUseCase(
            self.identity_database,
            self.id_provider,
            self.clock_provider,
            self.password_hashing_provider,
            self.action_token_provider,
            self.pending_handle_provider,
        )

    def test_should_create_one_pending_account_and_confirmation_contract(self) -> None:
        registration = AccountRegistration(
            display_name='  Pessoa Aprendente  ',
            email='  Learner@Example.COM ',
            password='secret123',  # noqa: S106
        )

        result = self.subject.execute(registration)

        assert result.pending_handle == 'pending-handle'
        assert result.account_id == '01JACCOUNT000000000000000001'
        assert result.identity_confirmation_id == '01JCONFIRM00000000000000001'
        assert result.communication_id == '01JCOMMUNICATION000000000001'
        assert result.confirmation_token == 'confirmation-token'
        assert result.confirmation_expires_at == self.now + timedelta(hours=24)

        account = self.repositories.accounts.add.call_args.args[0]
        assert account.id == result.account_id
        assert account.display_name == 'Pessoa Aprendente'
        assert account.email == 'learner@example.com'
        assert account.password_hash == 'argon2id-hash'
        assert account.status is AccountStatus.PENDING_CONFIRMATION
        assert account.created_at == self.now
        assert account.access_version == 1

        confirmation_token = self.repositories.account_action_tokens.add.call_args.args[
            0
        ]
        assert confirmation_token.id == result.identity_confirmation_id
        assert confirmation_token.account_id == result.account_id
        assert confirmation_token.token_hash == 'confirmation-token-hash'
        assert confirmation_token.communication_id == result.communication_id
        assert confirmation_token.pending_handle_hash == 'pending-handle-hash'
        assert confirmation_token.expires_at == result.confirmation_expires_at

        event = cast(
            'AccountCreatedEvent',
            self.repositories.events.add.call_args.args[0],
        )
        assert event.name == 'identity/account.created'
        assert event.payload.account_id == result.account_id
        assert event.payload.status is AccountStatus.PENDING_CONFIRMATION
        assert event.payload.created_at == self.now.isoformat()
        self.repositories.accounts.add.assert_called_once()
        self.repositories.account_action_tokens.add.assert_called_once()
        self.password_hashing_provider.hash.assert_called_once_with('secret123')

    @pytest.mark.parametrize(
        'status', [AccountStatus.ACTIVE, AccountStatus.PENDING_CONFIRMATION]
    )
    def test_should_return_same_private_duplicate_shape_without_new_state(
        self,
        status: AccountStatus,
    ) -> None:
        self.repositories.accounts.find_non_deleted_by_email.return_value = (
            AccountFaker.fake(
                status=status,
                email='learner@example.com',
            )
        )

        result = self.subject.execute(
            AccountRegistration(
                display_name='Outra Pessoa',
                email='LEARNER@example.com',
                password='secret123',  # noqa: S106
            )
        )

        assert result.pending_handle == 'pending-handle'
        assert result.account_id is None
        assert result.identity_confirmation_id is None
        assert result.communication_id is None
        assert result.confirmation_token is None
        assert result.confirmation_expires_at is None
        self.repositories.accounts.add.assert_not_called()
        self.repositories.account_action_tokens.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.id_provider.generate.assert_not_called()
        self.password_hashing_provider.hash.assert_not_called()
        self.action_token_provider.generate.assert_not_called()

    @pytest.mark.parametrize(
        ('display_name', 'email', 'password', 'error'),
        [
            ('   ', 'learner@example.com', 'secret123', InvalidDisplayNameError),
            ('Pessoa', 'not-an-email', 'secret123', InvalidEmailError),
            ('Pessoa', 'learner@example.com', 'short', InvalidPasswordError),
        ],
    )
    def test_should_reject_invalid_registration_values_before_use_case_execution(
        self,
        display_name: str,
        email: str,
        password: str,
        error: type[Exception],
    ) -> None:
        with pytest.raises(error):
            AccountRegistration(
                display_name=display_name,
                email=email,
                password=password,
            )

        self.identity_database.transaction.assert_not_called()
