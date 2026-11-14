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


_OLD_PASSWORD_HASH = 'old-password-hash'


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class _FixedTokenProvider:
    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class TestResetPasswordController:
    def test_reset_requires_bff_protection_and_rejects_invalid_payload(
        self,
        client: TestClient,
    ) -> None:
        unauthorized = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-resets',
                headers={'x-shifu-bff-secret': ''},
                json={
                    'token': 'recovery-token',
                    'password': 'new-password',
                    'password_confirmation': 'new-password',
                },
            ),
        )
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-resets',
                json={
                    'token': 'recovery-token',
                    'password': 'short',
                    'password_confirmation': 'short',
                },
            ),
        )

        assert unauthorized.status_code == 401
        assert invalid.status_code == 422
        assert invalid.json()['code'] == 'validation_error'

    def test_valid_reset_persists_password_token_and_access_facts(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        token = 'valid-recovery-token'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='reset@example.com',
                password_hash=_OLD_PASSWORD_HASH,
                status=AccountStatus.PENDING_CONFIRMATION,
                access_version=4,
                created_at=now,
                updated_at=now,
                confirmed_at=None,
            )
            repositories.accounts.add(account)
            for identifier, raw_token in (
                ('00000000000000000000000007', token),
                ('00000000000000000000000008', 'sibling-recovery-token'),
            ):
                repositories.account_action_tokens.add(
                    AccountActionToken(
                        id=identifier,
                        account_id=account.id,
                        type=AccountActionTokenType.PASSWORD_RECOVERY,
                        status=AccountActionTokenStatus.PENDING,
                        token_hash=_FixedTokenProvider.hash(raw_token),
                        issued_at=now - timedelta(minutes=1),
                        expires_at=now + timedelta(hours=1),
                        updated_at=now,
                        communication_id='00000000000000000000000009',
                    )
                )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _FixedTokenProvider()
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
                    '/identity/password-resets',
                    json={
                        'token': token,
                        'password': 'new-password',
                        'password_confirmation': 'new-password',
                    },
                ),
            )

        assert response.status_code == 200, response.text
        assert response.json() == {
            'result': 'reset',
            'account_id': account.id,
            'requires_email_confirmation': True,
            'access_version': 5,
        }
        with database.transaction() as repositories:
            persisted_account = repositories.accounts.find_by_id(account.id)
            assert persisted_account is not None
            assert persisted_account.password_hash != _OLD_PASSWORD_HASH
            assert persisted_account.access_version == 5
            assert persisted_account.status is AccountStatus.PENDING_CONFIRMATION
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id,
                    AccountActionTokenType.PASSWORD_RECOVERY,
                )
            )
            assert [token.status for token in tokens] == [
                AccountActionTokenStatus.USED,
                AccountActionTokenStatus.INVALIDATED,
            ]

    def test_expired_used_and_invalid_tokens_return_safe_results(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='terminal@example.com',
                created_at=now,
                updated_at=now,
            )
            repositories.accounts.add(account)
            for identifier, raw_token, token_status in (
                (
                    '00000000000000000000000010',
                    'expired-token',
                    AccountActionTokenStatus.EXPIRED,
                ),
                (
                    '00000000000000000000000011',
                    'used-token',
                    AccountActionTokenStatus.USED,
                ),
            ):
                repositories.account_action_tokens.add(
                    AccountActionToken(
                        id=identifier,
                        account_id=account.id,
                        type=AccountActionTokenType.PASSWORD_RECOVERY,
                        status=token_status,
                        token_hash=_FixedTokenProvider.hash(raw_token),
                        issued_at=now - timedelta(hours=2),
                        expires_at=now - timedelta(hours=1),
                        updated_at=now,
                        communication_id='00000000000000000000000012',
                    )
                )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _FixedTokenProvider()
        )
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            results = {
                raw_token: cast(
                    'Response',
                    client.post(  # pyright: ignore[reportUnknownMemberType]
                        '/identity/password-resets',
                        json={
                            'token': raw_token,
                            'password': 'new-password',
                            'password_confirmation': 'new-password',
                        },
                    ),
                ).json()
                for raw_token in ('expired-token', 'used-token', 'unknown-token')
            }

        assert results == {
            'expired-token': {
                'result': 'expired',
                'requires_email_confirmation': False,
            },
            'used-token': {'result': 'used', 'requires_email_confirmation': False},
            'unknown-token': {
                'result': 'invalid',
                'requires_email_confirmation': False,
            },
        }

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
                            '/identity/password-resets',
                            json={
                                'token': raw_token,
                                'password': 'new-password',
                                'password_confirmation': 'new-password',
                            },
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
                        assert rejected.status_code == 200
                        assert rejected.json()['result'] == 'invalid'
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
