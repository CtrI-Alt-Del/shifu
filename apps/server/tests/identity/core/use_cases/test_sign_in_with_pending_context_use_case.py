from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.identity.core.domain.enums import AccountAccess, AccountStatus
from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.domain.structures import (
    AccountProfile,
    AuthCredentials,
    Authentication,
)
from shifu.identity.core.use_cases import (
    IssuePendingConfirmationContextUseCase,
    SignInUseCase,
    SignInWithPendingContextUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


class TestSignInWithPendingContextUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sign_in_use_case = create_autospec(SignInUseCase, instance=True)
        self.issue_pending_context_use_case = create_autospec(
            IssuePendingConfirmationContextUseCase,
            instance=True,
        )
        self.credentials = AuthCredentials(
            email='learner@example.com',
            password='secret123',  # noqa: S106
        )
        self.subject = SignInWithPendingContextUseCase(
            sign_in_use_case=self.sign_in_use_case,
            issue_pending_confirmation_context_use_case=(
                self.issue_pending_context_use_case
            ),
        )

    @staticmethod
    def _authentication(
        access: AccountAccess,
        status: AccountStatus,
    ) -> Authentication:
        return Authentication(
            profile=AccountProfile(
                account_id='01JACCOUNT000000000000000001',
                display_name='Pessoa Aprendente',
                email='learner@example.com',
                time_zone=None,
                status=status,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                confirmed_at=None,
            ),
            access=access,
            access_version=1,
        )

    def test_should_return_protected_authentication_without_a_pending_handle(
        self,
    ) -> None:
        authentication = self._authentication(
            AccountAccess.PROTECTED,
            AccountStatus.ACTIVE,
        )
        self.sign_in_use_case.execute.return_value = authentication

        result = self.subject.execute(self.credentials)

        assert result == authentication
        assert result.pending_handle is None
        self.sign_in_use_case.execute.assert_called_once_with(self.credentials)
        self.issue_pending_context_use_case.execute.assert_not_called()

    def test_should_issue_a_pending_handle_for_activation_only_access(self) -> None:
        authentication = self._authentication(
            AccountAccess.ACTIVATION_ONLY,
            AccountStatus.PENDING_CONFIRMATION,
        )
        self.sign_in_use_case.execute.return_value = authentication
        self.issue_pending_context_use_case.execute.return_value = 'A' * 43

        result = self.subject.execute(self.credentials)

        assert result.profile == authentication.profile
        assert result.access is AccountAccess.ACTIVATION_ONLY
        assert result.access_version == authentication.access_version
        assert result.pending_handle == 'A' * 43
        self.issue_pending_context_use_case.execute.assert_called_once_with(
            authentication.profile.account_id
        )

    def test_should_not_issue_a_handle_when_credentials_are_rejected(self) -> None:
        self.sign_in_use_case.execute.side_effect = InvalidCredentialsError

        with pytest.raises(InvalidCredentialsError):
            self.subject.execute(self.credentials)

        self.issue_pending_context_use_case.execute.assert_not_called()

    def test_should_propagate_failure_to_issue_the_pending_handle(self) -> None:
        self.sign_in_use_case.execute.return_value = self._authentication(
            AccountAccess.ACTIVATION_ONLY,
            AccountStatus.PENDING_CONFIRMATION,
        )
        self.issue_pending_context_use_case.execute.side_effect = (
            ServiceUnavailableError
        )

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(self.credentials)
