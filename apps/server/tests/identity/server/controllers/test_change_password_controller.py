from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Event
from typing import TYPE_CHECKING, cast

import httpx2 as httpx
import pytest
from sqlalchemy import event, select

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
    AccountActionTokenDeliveryStatus,
)
from shifu.identity.pipes import IdentityPipe
from shifu.identity.providers.auth.password_hashing.argon2id_hash_provider import (
    Argon2idHashProvider,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from tests.fixtures.account_security_fixture import AccountSecurityFixture

if TYPE_CHECKING:
    from shifu.shared.core.domain.structures import AuthenticatedUser


def _seed_tokens(fixture: AccountSecurityFixture) -> None:
    now = datetime.now(UTC)
    with fixture.database.transaction() as repositories:
        for index, status in enumerate(AccountActionTokenStatus):
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id=str(index + 1).zfill(26),
                    account_id=fixture.account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=status,
                    token_hash=sha256(
                        ('recovery-' + status.value).encode()
                    ).hexdigest(),
                    pending_handle_hash=sha256(
                        ('handle-' + status.value).encode()
                    ).hexdigest(),
                    issued_at=now - timedelta(minutes=1),
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                    delivery_status=AccountActionTokenDeliveryStatus.DELIVERY_UNAVAILABLE,
                    communication_id=str(index + 20).zfill(26),
                )
            )


def _change(
    fixture: AccountSecurityFixture,
    current: str = 'current-password',
    new: str = 'new-password',
) -> int:
    return fixture.client.post(
        '/identity/accounts/me/password',
        headers=fixture.headers(),
        json={'current_password': current, 'new_password': new},
    ).status_code


def _run_race_operation(
    fixture: AccountSecurityFixture, operation: ContextVar[str], name: str
) -> tuple[int, dict[str, object]]:
    operation.set(name)
    if name == 'change':
        response = fixture.client.post(
            '/identity/accounts/me/password',
            headers=fixture.headers(),
            json={
                'current_password': 'current-password',
                'new_password': 'new-password',
            },
        )
    elif name == 'reset':
        response = fixture.client.post(
            '/identity/password-resets',
            json={
                'token': 'recovery-pending',
                'password': 'recovered-password',
                'password_confirmation': 'recovered-password',
            },
        )
    elif name == 'retry':
        response = fixture.client.post(
            '/identity/password-recoveries/retry',
            json={'recovery_handle': 'handle-pending'},
        )
    else:
        response = fixture.client.post(
            '/identity/password-recovery-requests',
            json={'email': fixture.account.email},
        )
    return response.status_code, response.json()


class TestChangePasswordController:
    def test_should_atomically_change_password_preserve_initiator_and_invalidate_pending_recovery(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        _seed_tokens(fixture)
        headers_a = fixture.headers()
        headers_b = fixture.headers(session='session-b')
        response = fixture.client.post(
            '/identity/accounts/me/password',
            headers=headers_a,
            json={
                'current_password': 'current-password',
                'new_password': 'new-password',
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == {'changed': True}
        assert (
            fixture.client.get('/identity/session', headers=headers_a).status_code
            == 200
        )
        assert (
            fixture.client.get('/identity/session', headers=headers_b).status_code
            == 401
        )
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.access_version == 5
            assert account.retained_session_id == 'session-a'
            assert account.retained_session_access_version == 4
            assert Argon2idHashProvider().verify('new-password', account.password_hash)
            assert not Argon2idHashProvider().verify(
                'current-password', account.password_hash
            )
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id, AccountActionTokenType.PASSWORD_RECOVERY
                )
            )
            assert all(
                token.status is not AccountActionTokenStatus.PENDING for token in tokens
            )
            assert {token.status for token in tokens} == {
                AccountActionTokenStatus.INVALIDATED,
                AccountActionTokenStatus.USED,
                AccountActionTokenStatus.EXPIRED,
            }
        with fixture.engine.connect() as connection:
            events = connection.execute(select(EventModel.__table__)).all()
        assert len(events) == 1
        assert 'current-password' not in str(events)
        assert 'session-a' not in str(events)
        # Same signed token can change again. A new session replaces its grant.
        assert _change(fixture, 'new-password', 'third-password') == 200
        assert (
            fixture.client.get('/identity/session', headers=headers_a).status_code
            == 200
        )
        session_c = fixture.headers(session='session-c', version=6)
        response = fixture.client.post(
            '/identity/accounts/me/password',
            headers=session_c,
            json={
                'current_password': 'third-password',
                'new_password': 'fourth-password',
            },
        )
        assert response.status_code == 200, response.text
        assert (
            fixture.client.get('/identity/session', headers=headers_a).status_code
            == 401
        )
        assert (
            fixture.client.get('/identity/session', headers=session_c).status_code
            == 200
        )

    @pytest.mark.parametrize(
        ('payload', 'status', 'code'),
        [
            (
                {'current_password': 'wrong', 'new_password': 'password'},
                403,
                'invalid_current_password',
            ),
            (
                {'current_password': '', 'new_password': 'password'},
                403,
                'invalid_current_password',
            ),
            (
                {'current_password': 'current-password', 'new_password': '1234567'},
                400,
                'invalid_new_password',
            ),
            (
                {'current_password': 'current-password', 'new_password': ''},
                400,
                'invalid_new_password',
            ),
            (
                {
                    'current_password': 'current-password',
                    'new_password': 'password',
                    'access_version': 9,
                },
                422,
                'validation_error',
            ),
            (
                {
                    'current_password': 'current-password',
                    'new_password': 'password',
                    'session_id': 'other',
                },
                422,
                'validation_error',
            ),
        ],
    )
    def test_should_reject_bad_input_without_partial_effect(
        self,
        account_security: AccountSecurityFixture,
        payload: dict[str, object],
        status: int,
        code: str,
    ) -> None:
        fixture = account_security
        _seed_tokens(fixture)
        response = fixture.client.post(
            '/identity/accounts/me/password', headers=fixture.headers(), json=payload
        )
        assert response.status_code == status, response.text
        assert response.json()['code'] == code
        self._assert_original_state(fixture)

    @pytest.mark.parametrize('phase', ['hash', 'write', 'event'])
    def test_should_rollback_all_effects_when_infrastructure_fails(
        self,
        account_security: AccountSecurityFixture,
        monkeypatch: pytest.MonkeyPatch,
        phase: str,
    ) -> None:
        fixture = account_security
        _seed_tokens(fixture)
        if phase == 'hash':

            class FailingHash:
                def verify(self, password: str, password_hash: str) -> bool:
                    return True

                def hash(self, password: str) -> str:
                    raise RuntimeError('private secret')

            fixture.app.dependency_overrides[
                IdentityPipe.get_password_hashing_provider
            ] = FailingHash

        def fail_write(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                phase == 'write' and statement.startswith('UPDATE identity_accounts')
            ) or (phase == 'event' and statement.startswith('INSERT INTO events')):
                raise RuntimeError('private secret')

        if phase != 'hash':
            event.listen(fixture.engine, 'before_cursor_execute', fail_write)
        try:
            response = fixture.client.post(
                '/identity/accounts/me/password',
                headers=fixture.headers(),
                json={
                    'current_password': 'current-password',
                    'new_password': 'new-password',
                },
            )
        finally:
            if phase != 'hash':
                event.remove(fixture.engine, 'before_cursor_execute', fail_write)
        assert response.status_code == 503, response.text
        assert response.json()['code'] == 'service_unavailable'
        assert 'private secret' not in response.text
        self._assert_original_state(fixture)

    @staticmethod
    def _assert_original_state(fixture: AccountSecurityFixture) -> None:
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.password_hash == fixture.account.password_hash
            assert account.access_version == 4
            assert account.retained_session_id is None
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id, AccountActionTokenType.PASSWORD_RECOVERY
                )
            )
            assert {token.status for token in tokens} == set(AccountActionTokenStatus)
        with fixture.engine.connect() as connection:
            assert connection.execute(select(EventModel.__table__)).all() == []

    def test_should_reject_authentication_snapshot_obtained_before_revocation(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        user = fixture.app.state.authentication_provider.authenticate(fixture.token())
        assert _change(fixture) == 200
        fixture.app.dependency_overrides[IdentityPipe.get_authenticated_user] = lambda: (
            user
        )
        response = fixture.client.post(
            '/identity/accounts/me/password',
            headers=fixture.headers(),
            json={'current_password': 'new-password', 'new_password': 'third-password'},
        )
        assert response.status_code == 401, response.text
        assert response.json()['code'] == 'unauthorized'
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.access_version == 5
            assert Argon2idHashProvider().verify('new-password', account.password_hash)

    @pytest.mark.parametrize('first', ['a', 'b'])
    def test_should_serialize_distinct_password_changes_in_both_commit_orders(
        self,
        account_security: AccountSecurityFixture,
        first: str,
    ) -> None:
        fixture = account_security
        users = {
            session: cast(
                'AuthenticatedUser',
                fixture.app.state.authentication_provider.authenticate(
                    fixture.token(session=session)
                ),
            )
            for session in ('a', 'b')
        }
        selected = ContextVar('account-race-session', default='')
        fixture.app.dependency_overrides[IdentityPipe.get_authenticated_user] = lambda: (
            users[selected.get()]
        )
        acquired, release, second_started = Event(), Event(), Event()
        second = 'b' if first == 'a' else 'a'

        def before(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                selected.get() == second
                and 'identity_accounts' in statement
                and 'FOR UPDATE' in statement
            ):
                second_started.set()

        def after(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                selected.get() == first
                and 'identity_accounts' in statement
                and 'FOR UPDATE' in statement
            ):
                acquired.set()
                if not release.wait(timeout=15):
                    raise TimeoutError('Second mutation did not contend')

        def change(session: str) -> int:
            selected.set(session)
            return _change(fixture)

        event.listen(fixture.engine, 'before_cursor_execute', before)
        event.listen(fixture.engine, 'after_cursor_execute', after)
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(change, first)
                try:
                    assert acquired.wait(timeout=15)
                    second_future = executor.submit(change, second)
                    assert second_started.wait(timeout=15)
                finally:
                    release.set()
                assert first_future.result(timeout=20) == 200
                assert second_future.result(timeout=20) == 401
        finally:
            release.set()
            event.remove(fixture.engine, 'before_cursor_execute', before)
            event.remove(fixture.engine, 'after_cursor_execute', after)
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.access_version == 5
            assert account.retained_session_id == first

    @pytest.mark.parametrize('other', ['reset', 'retry', 'request'])
    @pytest.mark.parametrize('change_first', [True, False])
    def test_should_serialize_change_against_recovery_in_both_commit_orders(
        self,
        account_security: AccountSecurityFixture,
        other: str,
        change_first: bool,
    ) -> None:
        fixture = account_security
        _seed_tokens(fixture)
        first = 'change' if change_first else other
        second = other if change_first else 'change'
        operation = ContextVar('account-test-operation', default='')
        acquired, release, second_started = Event(), Event(), Event()
        counts: dict[str, int] = {}

        def before(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            if (
                operation.get() == second
                and 'identity_accounts' in statement
                and 'FOR UPDATE' in statement
            ):
                second_started.set()

        def after(
            connection: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            current = operation.get()
            if (
                current != first
                or 'identity_accounts' not in statement
                or 'FOR UPDATE' not in statement
            ):
                return
            counts[current] = counts.get(current, 0) + 1
            # A change authenticates in its first transaction and mutates in its
            # second. Recovery locks the account in its sole first transaction.
            if counts[current] != (2 if current == 'change' else 1):
                return
            acquired.set()
            if not release.wait(timeout=15):
                raise TimeoutError('Competing HTTP operation did not start')

        event.listen(fixture.engine, 'before_cursor_execute', before)
        event.listen(fixture.engine, 'after_cursor_execute', after)
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(
                    _run_race_operation, fixture, operation, first
                )
                try:
                    assert acquired.wait(timeout=15), (
                        'First HTTP mutation did not acquire account lock'
                    )
                    second_future = executor.submit(
                        _run_race_operation, fixture, operation, second
                    )
                    assert second_started.wait(timeout=15), (
                        'Second HTTP request did not contend on account lock'
                    )
                finally:
                    release.set()
                results = {
                    first: first_future.result(timeout=25),
                    second: second_future.result(timeout=25),
                }
        finally:
            release.set()
            event.remove(fixture.engine, 'before_cursor_execute', before)
            event.remove(fixture.engine, 'after_cursor_execute', after)
        if other == 'reset':
            assert results['change'][0] == (200 if change_first else 401), results
            assert results['reset'][1]['result'] == (
                'invalid' if change_first else 'reset'
            ), results
        else:
            assert results['change'][0] == 200, results
            assert results[other][0] == 202, results
            if other == 'retry':
                assert results['retry'][1]['is_decoy'] is change_first
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.access_version == 5
            assert account.retained_session_id == (
                None if other == 'reset' and not change_first else 'session-a'
            )
            pending = repositories.account_action_tokens.find_many_pending_by_account_id_and_type(
                fixture.account.id, AccountActionTokenType.PASSWORD_RECOVERY
            )
            assert len(pending) == (1 if other == 'request' and change_first else 0)

    def test_should_confirm_real_sign_in_uses_changed_credential(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        assert _change(fixture) == 200
        old = fixture.client.post(
            '/identity/sign-in',
            json={'email': fixture.account.email, 'password': 'current-password'},
        )
        new = fixture.client.post(
            '/identity/sign-in',
            json={'email': fixture.account.email, 'password': 'new-password'},
        )
        assert old.status_code == 401
        assert new.status_code == 200
        assert new.json()['profile']['account_id'] == fixture.account.id

    def test_should_preserve_committed_result_when_response_is_lost(
        self, account_security: AccountSecurityFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fixture = account_security
        real_send = fixture.client.send

        def lose_response(
            request: httpx.Request,
            *,
            stream: bool = False,
            auth: httpx.Auth | None = None,
            follow_redirects: bool = False,
        ) -> httpx.Response:
            response = real_send(
                request, stream=stream, auth=auth, follow_redirects=follow_redirects
            )
            response.close()
            raise httpx.ReadError('Response unavailable', request=request)

        with monkeypatch.context() as patch:
            patch.setattr(fixture.client, 'send', lose_response)
            with pytest.raises(httpx.ReadError):
                _change(fixture)
        assert (
            fixture.client.get(
                '/identity/session', headers=fixture.headers()
            ).status_code
            == 200
        )
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.access_version == 5
            assert account.retained_session_id == 'session-a'
            assert Argon2idHashProvider().verify('new-password', account.password_hash)
