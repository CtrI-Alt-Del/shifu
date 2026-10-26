from datetime import UTC, datetime

import pytest

from shifu.identity.core.domain.enums import AccountStatus
from tests.fixtures.account_security_fixture import AccountSecurityFixture


class TestGetAccountProfileController:
    def test_should_return_full_real_profile_without_internal_grant(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        fixture.account.time_zone = None
        with fixture.database.transaction() as repositories:
            repositories.accounts.update(fixture.account)
        response = fixture.client.get(
            '/identity/accounts/me', headers=fixture.headers()
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            'account_id': fixture.account.id,
            'display_name': fixture.account.display_name,
            'email': fixture.account.email,
            'time_zone': None,
            'status': 'active',
            'created_at': fixture.account.created_at.isoformat().replace('+00:00', 'Z'),
            'confirmed_at': fixture.account.confirmed_at.isoformat().replace(
                '+00:00', 'Z'
            )
            if fixture.account.confirmed_at
            else None,
        }

    @pytest.mark.parametrize(
        'kind',
        [
            'absent',
            'expired',
            'tampered',
            'revoked',
            'missing',
            'pending',
            'deleted',
            'no-bff',
        ],
    )
    def test_should_reject_invalid_access(
        self, account_security: AccountSecurityFixture, kind: str
    ) -> None:
        fixture = account_security
        headers = fixture.headers()
        if kind == 'absent':
            headers = {}
        elif kind == 'expired':
            headers = fixture.headers(exp=datetime(2000, 1, 1, tzinfo=UTC))
        elif kind == 'tampered':
            token = fixture.token()
            headers = {'Authorization': 'Bearer ' + token[:-8] + 'badtoken'}
        elif kind == 'revoked':
            headers = fixture.headers(version=3)
        elif kind == 'missing':
            headers = fixture.headers(account_id='00000000000000000000000000')
        elif kind in {'pending', 'deleted'}:
            if kind == 'deleted':
                fixture.account.delete(datetime.now(UTC))
            else:
                fixture.account.status = AccountStatus.PENDING_CONFIRMATION
                fixture.account.confirmed_at = None
            with fixture.database.transaction() as repositories:
                repositories.accounts.update(fixture.account)
        elif kind == 'no-bff':
            headers['x-shifu-bff-secret'] = ''
        response = fixture.client.get('/identity/accounts/me', headers=headers)
        assert response.status_code == 401, response.text
        assert 'password' not in response.text
        assert 'session' not in response.text
