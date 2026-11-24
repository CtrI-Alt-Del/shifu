from tests.fixtures.account_security_fixture import AccountSecurityFixture


class TestAccountActivityAdmissionController:
    def test_should_admit_only_the_retained_session_after_password_change(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        fixture.account.retained_session_id = 'retained-session'
        fixture.account.retained_session_access_version = (
            fixture.account.access_version - 1
        )
        with fixture.database.transaction() as repositories:
            repositories.accounts.update(fixture.account)

        retained = fixture.client.post(
            '/identity/internal/account-activity-admissions',
            json={
                'account_id': fixture.account.id,
                'access_version': fixture.account.retained_session_access_version,
                'session_id': 'retained-session',
            },
        )
        stale_without_session = fixture.client.post(
            '/identity/internal/account-activity-admissions',
            json={
                'account_id': fixture.account.id,
                'access_version': fixture.account.retained_session_access_version,
            },
        )
        stale_other_session = fixture.client.post(
            '/identity/internal/account-activity-admissions',
            json={
                'account_id': fixture.account.id,
                'access_version': fixture.account.retained_session_access_version,
                'session_id': 'revoked-session',
            },
        )

        assert retained.status_code == 204
        assert stale_without_session.status_code == 401
        assert stale_other_session.status_code == 401
