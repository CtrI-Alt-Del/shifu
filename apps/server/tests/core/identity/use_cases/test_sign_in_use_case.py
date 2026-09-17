from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.domain.enums import AccountAccess, AccountStatus
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.domain.structures import (
    AccountProfile,
    AuthCredentials,
    Authentication,
)
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.identity.core.use_cases.sign_in_use_case import SignInUseCase


class TestSignInUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.identity_database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = (
            self.identity_database.transaction.return_value.__enter__.return_value
        )
        self.accounts_repository = self.repositories.accounts
        self.password_hashing_provider = create_autospec(
            PasswordHashingProvider,
            instance=True,
        )
        self.subject = SignInUseCase(
            self.identity_database,
            self.password_hashing_provider,
        )

    def test_should_return_protected_authentication_for_active_account(self) -> None:
        account = AccountFaker.fake(
            id='01JACCOUNT000000000000000001',
            display_name='Pessoa Aprendente',
            email='learner@example.com',
            password_hash='stored-hash',  # noqa: S106
            access_version=4,
            time_zone='America/Sao_Paulo',
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            confirmed_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        self.accounts_repository.find_non_deleted_by_email.return_value = account
        self.password_hashing_provider.verify.return_value = True

        result = self.subject.execute(
            AuthCredentials(
                email='  learner@example.com  ',
                password='secret',  # noqa: S106
            )
        )

        assert result == Authentication(
            profile=AccountProfile(
                account_id=account.id,
                display_name=account.display_name,
                email=account.email,
                time_zone=account.time_zone,
                status=account.status,
                created_at=account.created_at,
                confirmed_at=account.confirmed_at,
            ),
            access=AccountAccess.PROTECTED,
            access_version=4,
        )
        self.accounts_repository.find_non_deleted_by_email.assert_called_once_with(
            'learner@example.com'
        )
        self.password_hashing_provider.verify.assert_called_once_with(
            'secret',
            'stored-hash',
        )
        self.identity_database.transaction.assert_called_once_with()

    def test_should_return_activation_only_for_pending_account(self) -> None:
        account = AccountFaker.fake(
            status=AccountStatus.PENDING_CONFIRMATION,
            password_hash='stored-hash',  # noqa: S106
            access_version=2,
        )
        self.accounts_repository.find_non_deleted_by_email.return_value = account
        self.password_hashing_provider.verify.return_value = True

        result = self.subject.execute(
            AuthCredentials(email=account.email, password='secret')  # noqa: S106
        )

        assert result.access is AccountAccess.ACTIVATION_ONLY
        assert result.access_version == account.access_version
        assert result.profile.status is AccountStatus.PENDING_CONFIRMATION
        self.password_hashing_provider.verify.assert_called_once_with(
            'secret',
            'stored-hash',
        )

    @pytest.mark.parametrize(
        ('status', 'email', 'password', 'verify_result'),
        [
            (None, 'unknown@example.com', 'secret', None),
            (None, 'Learner@example.com', 'secret', None),
            (AccountStatus.DELETED, 'deleted@example.com', 'secret', True),
            (AccountStatus.ACTIVE, 'valid@example.com', 'wrong', False),
        ],
    )
    def test_should_raise_generic_error_for_invalid_credentials(
        self,
        status: AccountStatus | None,
        email: str,
        password: str,
        verify_result: bool | None,
    ) -> None:
        account = (
            AccountFaker.fake(
                email=email,
                status=status,
                password_hash='stored-hash',  # noqa: S106
            )
            if status is not None
            else None
        )
        self.accounts_repository.find_non_deleted_by_email.return_value = account
        self.password_hashing_provider.verify.return_value = verify_result

        with pytest.raises(InvalidCredentialsError):
            self.subject.execute(AuthCredentials(email=email, password=password))

        if account is None:
            self.password_hashing_provider.verify.assert_not_called()
        else:
            self.password_hashing_provider.verify.assert_called_once()
