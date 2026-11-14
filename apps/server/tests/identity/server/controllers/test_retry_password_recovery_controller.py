from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Event
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient
from sqlalchemy import event

from shifu.app import FastAPIApp
from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountStatus,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from httpx import Response

    from tests.fixtures.postgres_fixture import PostgresDatabase


class _FixedTokenProvider:
    def __init__(self, token: str) -> None:
        self._token = token

    def generate(self) -> str:
        return self._token

    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class TestRetryPasswordRecoveryController:
    def test_retry_requires_bff_protection_and_valid_context(
        self,
        client: TestClient,
    ) -> None:
        unauthorized = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recoveries/retry',
                headers={'x-shifu-bff-secret': ''},
                json={'recovery_handle': 'opaque-handle'},
            ),
        )
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recoveries/retry',
                json={'recovery_handle': ''},
            ),
        )

        assert unauthorized.status_code == 401
        assert invalid.status_code == 422
        assert invalid.json()['code'] == 'validation_error'

    def test_terminal_delivery_issue_replaces_the_persisted_recovery_token(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        handle = 'retry-handle'
        old_token = 'old-recovery-token'
        replacement_token = 'replacement-recovery-token'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='retry@example.com',
                created_at=now,
                updated_at=now,
            )
            repositories.accounts.add(account)
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000005',
                    account_id=account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=_FixedTokenProvider.hash(old_token),
                    issued_at=now - timedelta(minutes=2),
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                    communication_id='00000000000000000000000006',
                    pending_handle_hash=_FixedTokenProvider.hash(handle),
                    delivery_status=AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                )
            )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _FixedTokenProvider(replacement_token)
        )
        app.dependency_overrides[IdentityPipe.get_recovery_handle_provider] = lambda: (
            _FixedTokenProvider(handle)
        )
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recoveries/retry',
                    json={'recovery_handle': handle},
                ),
            )

        assert response.status_code == 202
        assert response.json() == {'recovery_handle': handle, 'is_decoy': False}
        with database.transaction() as repositories:
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id,
                    AccountActionTokenType.PASSWORD_RECOVERY,
                )
            )
            assert len(tokens) == 2
            assert tokens[0].status is AccountActionTokenStatus.INVALIDATED
            assert tokens[1].status is AccountActionTokenStatus.PENDING
            assert tokens[1].token_hash == _FixedTokenProvider.hash(replacement_token)

    def test_should_reject_confirmation_token_without_inverse_lock_while_confirmation_runs(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        raw_token = 'A' * 43
        raw_handle = 'wrong-type-confirmation-handle'
        database = SqlalchemyIdentityDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                status=AccountStatus.PENDING_CONFIRMATION,
                access_version=1,
                created_at=now,
                updated_at=now,
                confirmed_at=None,
            )
            repositories.accounts.add(account)
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000971',
                    account_id=account.id,
                    type=AccountActionTokenType.EMAIL_CONFIRMATION,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=sha256(raw_token.encode()).hexdigest(),
                    pending_handle_hash=sha256(raw_handle.encode()).hexdigest(),
                    communication_id='00000000000000000000000972',
                    issued_at=now,
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                )
            )
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        operation = ContextVar('wrong-type-recovery-operation', default='')
        token_locked, release_confirmation = Event(), Event()
        inverse_account_locks: list[str] = []

        def inspect_lock(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                operation.get() == 'wrong-type'
                and 'identity_accounts' in statement
                and 'FOR UPDATE' in statement
            ):
                inverse_account_locks.append(statement)

        def hold_confirmation_token(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                operation.get() != 'confirmation'
                or 'identity_account_action_tokens' not in statement
                or 'FOR UPDATE' not in statement
            ):
                return
            token_locked.set()
            if not release_confirmation.wait(timeout=15):
                raise TimeoutError(
                    'Wrong-type recovery did not finish while confirmation held its token'
                )

        event.listen(postgres_database.engine, 'before_cursor_execute', inspect_lock)
        event.listen(
            postgres_database.engine, 'after_cursor_execute', hold_confirmation_token
        )
        try:
            with TestClient(
                app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
            ) as client:

                def confirm() -> Response:
                    operation.set('confirmation')
                    return cast(
                        'Response',
                        client.post(
                            '/identity/email-confirmations', json={'token': raw_token}
                        ),
                    )

                def reject_wrong_type() -> Response:
                    operation.set('wrong-type')
                    return cast(
                        'Response',
                        client.post(
                            '/identity/password-recoveries/retry',
                            json={'recovery_handle': raw_handle},
                        ),
                    )

                with ThreadPoolExecutor(max_workers=2) as executor:
                    confirmation = executor.submit(confirm)
                    try:
                        assert token_locked.wait(timeout=10), (
                            'Confirmation did not acquire its token lock'
                        )
                        rejection = executor.submit(reject_wrong_type)
                        rejected = rejection.result(timeout=10)
                        assert rejected.status_code == 202
                        assert rejected.json()['is_decoy'] is True
                        assert inverse_account_locks == []
                        assert not confirmation.done(), (
                            'Confirmation must still be paused before locking the account'
                        )
                    finally:
                        release_confirmation.set()
                    confirmed = confirmation.result(timeout=10)
                    assert confirmed.status_code == 200, confirmed.text
                    assert confirmed.json()['result'] == 'activated'
        finally:
            release_confirmation.set()
            event.remove(
                postgres_database.engine, 'before_cursor_execute', inspect_lock
            )
            event.remove(
                postgres_database.engine,
                'after_cursor_execute',
                hold_confirmation_token,
            )
            app.dependency_overrides.clear()
        with database.transaction() as repositories:
            persisted = repositories.accounts.find_by_id(account.id)
            assert persisted is not None
            assert persisted.status is AccountStatus.ACTIVE
            assert persisted.password_hash == account.password_hash
            assert persisted.access_version == 2
            token = repositories.account_action_tokens.find_by_hash(
                sha256(raw_token.encode()).hexdigest()
            )
            assert token is not None
            assert token.status is AccountActionTokenStatus.USED
