from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from tests.fixtures.account_security_fixture import AccountSecurityFixture


class TestGetCurrentSessionController:
    def test_should_keep_rejection_safe(self, client: TestClient) -> None:
        response = client.get('/identity/session')
        assert response.status_code == 401
        body = response.json()
        assert body['detail']['code'] == 'unauthorized'
        assert 'account' not in str(body).lower()

    @pytest.mark.parametrize(
        'claims',
        [
            {'sid': ''},
            {'sid': 42},
            {'access_version': True},
            {'access_version': 0},
            {'access_version': '4'},
            {'iat': True},
            {'exp': True},
            {'jti': ''},
            {'aud': 'other'},
            {'iss': 'other'},
            {'sub': ''},
        ],
    )
    def test_should_validate_real_signed_claims(
        self, account_security: AccountSecurityFixture, claims: dict[str, object]
    ) -> None:
        fixture = account_security
        response = fixture.client.get(
            '/identity/session', headers=fixture.headers(claims=claims)
        )
        assert response.status_code == 401

    def test_should_accept_only_exact_retained_pair_and_revoke_it_on_recovery(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        headers_a = fixture.headers()
        headers_b = fixture.headers(session='session-b')
        changed = fixture.client.post(
            '/identity/accounts/me/password',
            headers=headers_a,
            json={
                'current_password': 'current-password',
                'new_password': 'new-password',
            },
        )
        assert changed.status_code == 200, changed.text
        session = fixture.client.get('/identity/session', headers=headers_a)
        assert session.status_code == 200
        assert set(session.json()) == {'account_id', 'display_name', 'time_zone'}
        assert (
            fixture.client.get('/identity/session', headers=headers_b).status_code
            == 401
        )
        assert (
            fixture.client.get(
                '/identity/session', headers=fixture.headers(version=3)
            ).status_code
            == 401
        )
        assert (
            fixture.client.get(
                '/identity/session',
                headers=fixture.headers(session='new-session', version=5),
            ).status_code
            == 200
        )
        now = datetime.now(UTC)
        with fixture.database.transaction() as repositories:
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000888',
                    account_id=fixture.account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=sha256(b'future-recovery').hexdigest(),
                    communication_id='00000000000000000000000889',
                    issued_at=now,
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                )
            )
        reset = fixture.client.post(
            '/identity/password-resets',
            json={
                'token': 'future-recovery',
                'password': 'recovered-password',
                'password_confirmation': 'recovered-password',
            },
        )
        assert reset.status_code == 200, reset.text
        assert reset.json()['result'] == 'reset'
        assert (
            fixture.client.get('/identity/session', headers=headers_a).status_code
            == 401
        )
        assert (
            fixture.client.get(
                '/identity/session', headers=fixture.headers(version=5)
            ).status_code
            == 401
        )
        assert (
            fixture.client.get(
                '/identity/session', headers=fixture.headers(version=6)
            ).status_code
            == 200
        )
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.retained_session_id is None
            assert account.retained_session_access_version is None
