from uuid import uuid4

from shifu.identity.core.domain.enums import AccountStatus
from tests.fixtures.account_security_fixture import AccountSecurityFixture


class TestDeleteAccountController:
    def test_should_close_the_authenticated_account_and_reject_old_session(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        erasure_id = uuid4()
        response = fixture.client.post(
            '/identity/account-deletions',
            headers=fixture.headers(),
            json={
                'erasure_id': str(erasure_id),
                'current_password': 'current-password',
                'confirmed': True,
            },
        )

        assert response.status_code == 202, response.text
        assert set(response.json()) == {'state', 'closed_at', 'erasure'}
        assert response.json()['state'] == 'closed'
        assert response.json()['erasure'] == 'pending'
        assert (
            fixture.client.get(
                '/identity/session', headers=fixture.headers()
            ).status_code
            == 401
        )
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.status is AccountStatus.DELETED
            result = repositories.account_erasures.find_result(erasure_id)
            assert result is not None
            assert result.erasure == 'pending'

    def test_should_reject_wrong_password_without_closing_the_account(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        response = fixture.client.post(
            '/identity/account-deletions',
            headers=fixture.headers(),
            json={
                'erasure_id': str(uuid4()),
                'current_password': 'wrong-password',
                'confirmed': True,
            },
        )

        assert response.status_code == 403
        assert response.json() == {
            'code': 'invalid_current_password',
            'message': 'A senha atual está incorreta.',
        }
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.status is AccountStatus.ACTIVE

    def test_should_reject_unconfirmed_or_arbitrary_account_requests(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        common_body = {
            'erasure_id': str(uuid4()),
            'current_password': 'current-password',
        }

        unconfirmed = fixture.client.post(
            '/identity/account-deletions',
            headers=fixture.headers(),
            json={**common_body, 'confirmed': False},
        )
        arbitrary_account = fixture.client.post(
            '/identity/account-deletions',
            headers=fixture.headers(),
            json={
                **common_body,
                'confirmed': True,
                'account_id': 'another-account',
            },
        )

        assert unconfirmed.status_code == 422
        assert arbitrary_account.status_code == 422
        with fixture.database.transaction() as repositories:
            account = repositories.accounts.find_by_id(fixture.account.id)
            assert account is not None
            assert account.status is AccountStatus.ACTIVE
