from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.interfaces import (
    IdentityDatabase,
    IdentityDatabaseRepositories,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from datetime import timedelta

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.core.domain.errors import (
    InvalidPasswordError,
    InvalidCredentialsError,
)
from shifu.identity.core.domain.events import AccountActionTokenCancelledEvent
from shifu.identity.core.domain.structures import PasswordChangeRequest
from shifu.identity.core.interfaces import PasswordHashingProvider
from shifu.identity.core.use_cases import ChangePasswordUseCase


class TestChangePasswordUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IdentityDatabase, instance=True)
        self.repositories = create_autospec(IdentityDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 10, 25, tzinfo=UTC)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.account = AccountFaker.fake(access_version=4)
        self.user = AuthenticatedUser(
            account_id=self.account.id,
            display_name=self.account.display_name,
            time_zone=self.account.time_zone,
            session_id='session-a',
            token_access_version=4,
            account_access_version=4,
        )
        self.repositories.accounts.find_by_id.return_value = self.account
        self.hasher = create_autospec(PasswordHashingProvider, instance=True)
        self.hasher.verify.return_value = True
        self.hasher.hash.return_value = 'new-hash'
        self.token_hash = 'test-token-hash'
        self.old_password = 'old'
        self.valid_password = 'password'
        self.wrong_password = 'wrong'
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = []
        self.subject = ChangePasswordUseCase(self.database, self.clock, self.hasher)

    @pytest.mark.parametrize(
        'password', ['12345678', 'á' * 8, '   spaces  ', 'same-password']
    )
    def test_should_preserve_initiator_and_revoke_other_accesses(
        self, password: str
    ) -> None:
        old_hash = self.account.password_hash
        self.subject.execute(
            self.user,
            PasswordChangeRequest(current_password=password, new_password=password),
        )
        assert self.account.password_hash == 'new-hash'
        assert self.account.access_version == 5
        assert self.account.retained_session_id == 'session-a'
        assert self.account.retained_session_access_version == 4
        assert self.account.accepts_access('session-a', 4)
        assert not self.account.accepts_access('session-b', 4)
        self.hasher.verify.assert_called_once_with(password, old_hash)
        self.hasher.hash.assert_called_once_with(password)
        self.repositories.accounts.update.assert_called_once_with(self.account)

    def test_should_support_repeated_changes_and_new_session_replacement(self) -> None:
        self.subject.execute(
            self.user,
            PasswordChangeRequest(
                current_password=self.old_password, new_password=self.valid_password
            ),
        )
        user = AuthenticatedUser(
            account_id=self.account.id,
            display_name='Name',
            time_zone=None,
            session_id='session-a',
            token_access_version=4,
            account_access_version=5,
        )
        self.subject.execute(
            user,
            PasswordChangeRequest(
                current_password=self.valid_password, new_password=self.valid_password
            ),
        )
        assert self.account.access_version == 6
        assert self.account.accepts_access('session-a', 4)
        user = AuthenticatedUser(
            account_id=self.account.id,
            display_name='Name',
            time_zone=None,
            session_id='session-c',
            token_access_version=6,
            account_access_version=6,
        )
        self.subject.execute(
            user,
            PasswordChangeRequest(
                current_password=self.valid_password, new_password=self.valid_password
            ),
        )
        assert self.account.access_version == 7
        assert self.account.accepts_access('session-c', 6)
        assert not self.account.accepts_access('session-a', 4)

    @pytest.mark.parametrize('password', ['', '1234567', 'á' * 7])
    def test_should_reject_short_new_password_before_effects(
        self, password: str
    ) -> None:
        with pytest.raises(InvalidPasswordError):
            self.subject.execute(
                self.user,
                PasswordChangeRequest(
                    current_password=self.old_password, new_password=password
                ),
            )
        self.database.transaction.assert_not_called()

    def test_should_reject_wrong_current_password_without_side_effects(self) -> None:
        self.hasher.verify.return_value = False
        original = (self.account.password_hash, self.account.access_version)
        with pytest.raises(InvalidCredentialsError):
            self.subject.execute(
                self.user,
                PasswordChangeRequest(
                    current_password=self.wrong_password,
                    new_password=self.valid_password,
                ),
            )
        assert (self.account.password_hash, self.account.access_version) == original
        self.hasher.hash.assert_not_called()
        self.repositories.accounts.update.assert_not_called()
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_stale_snapshot_before_verifying_password(self) -> None:
        self.account.access_version = 5
        with pytest.raises(AuthorizationError):
            self.subject.execute(
                self.user,
                PasswordChangeRequest(
                    current_password=self.old_password, new_password=self.valid_password
                ),
            )
        self.hasher.verify.assert_not_called()
        self.repositories.accounts.update.assert_not_called()

    def test_should_invalidate_pending_recovery_and_emit_only_associated_cancellation(
        self,
    ) -> None:
        tokens = [
            AccountActionToken(
                id='token-' + str(i),
                account_id=self.account.id,
                type=AccountActionTokenType.PASSWORD_RECOVERY,
                status=AccountActionTokenStatus.PENDING,
                token_hash='hash-' + str(i),
                issued_at=self.now,
                expires_at=self.now + timedelta(hours=1),
                updated_at=self.now,
                communication_id='communication' if i == 0 else None,
            )
            for i in range(2)
        ]
        self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = tokens
        self.subject.execute(
            self.user,
            PasswordChangeRequest(
                current_password=self.old_password, new_password=self.valid_password
            ),
        )
        assert all(
            token.status is AccountActionTokenStatus.INVALIDATED for token in tokens
        )
        assert self.repositories.account_action_tokens.update.call_count == 2
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, AccountActionTokenCancelledEvent)
        assert event.payload.communication_id == 'communication'
        assert event.payload.identity_action_token_id == 'token-0'
        assert event.payload.reason.value == 'reset'
        self.repositories.events.add.assert_called_once()

    def test_should_leave_state_untouched_when_hashing_fails(self) -> None:
        self.hasher.hash.side_effect = RuntimeError('private failure')
        original = (self.account.password_hash, self.account.access_version)
        with pytest.raises(RuntimeError):
            self.subject.execute(
                self.user,
                PasswordChangeRequest(
                    current_password=self.old_password, new_password=self.valid_password
                ),
            )
        assert (self.account.password_hash, self.account.access_version) == original
        self.repositories.accounts.update.assert_not_called()
        assert (
            self.database.transaction.return_value.__exit__.call_args.args[0]
            is RuntimeError
        )

    @pytest.mark.parametrize(
        'context',
        [
            'missing',
            'pending',
            'deleted',
            'wrong-session',
            'wrong-version',
            'unknown-account',
        ],
    )
    def test_should_reject_invalid_context_without_sensitive_effects(
        self, context: str
    ) -> None:
        if context == 'unknown-account':
            self.repositories.accounts.find_by_id.return_value = None
        elif context in {'pending', 'deleted'}:
            self.account.status = (
                AccountStatus.PENDING_CONFIRMATION
                if context == 'pending'
                else AccountStatus.DELETED
            )
        else:
            self.account.retained_session_id = 'session-a'
            self.account.retained_session_access_version = 3
        user = AuthenticatedUser(
            account_id=self.account.id,
            display_name='Name',
            time_zone=None,
            session_id=None
            if context == 'missing'
            else 'session-b'
            if context == 'wrong-session'
            else 'session-a',
            token_access_version=2 if context == 'wrong-version' else 3,
            account_access_version=4,
        )
        with pytest.raises(AuthorizationError):
            self.subject.execute(
                user,
                PasswordChangeRequest(
                    current_password=self.old_password, new_password=self.valid_password
                ),
            )
        self.hasher.verify.assert_not_called()
        self.hasher.hash.assert_not_called()
        self.repositories.accounts.update.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize('phase', ['write', 'outbox'])
    def test_should_propagate_failure_through_transaction_owner(
        self, phase: str
    ) -> None:
        if phase == 'write':
            self.repositories.accounts.update.side_effect = RuntimeError('unavailable')
        else:
            token = AccountActionToken(
                id='token-id',
                account_id=self.account.id,
                type=AccountActionTokenType.PASSWORD_RECOVERY,
                status=AccountActionTokenStatus.PENDING,
                token_hash=self.token_hash,
                issued_at=self.now,
                expires_at=self.now + timedelta(hours=1),
                updated_at=self.now,
                communication_id='communication-id',
            )
            self.repositories.account_action_tokens.find_many_pending_by_account_id_and_type.return_value = [
                token
            ]
            self.repositories.events.add.side_effect = RuntimeError('unavailable')
        with pytest.raises(RuntimeError):
            self.subject.execute(
                self.user,
                PasswordChangeRequest(
                    current_password=self.old_password, new_password=self.valid_password
                ),
            )
        assert (
            self.database.transaction.return_value.__exit__.call_args.args[0]
            is RuntimeError
        )
        if phase == 'write':
            self.repositories.events.add.assert_not_called()
