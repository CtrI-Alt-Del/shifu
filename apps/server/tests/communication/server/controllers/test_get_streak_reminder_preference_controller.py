from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
PATH = '/communication/streak-reminder-preference'
FIRST_USER = {'Authorization': 'Bearer test-access-token'}
SECOND_USER = {'Authorization': 'Bearer other-access-token'}


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'test-access-token': ACCOUNT_ID,
            'other-access-token': OTHER_ACCOUNT_ID,
        }
        if access_token not in accounts:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=accounts[access_token],
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
            session_id='test-session',
            token_access_version=1,
            account_access_version=1,
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(postgres_database.engine)
    identity_database = SqlalchemyIdentityDatabase(postgres_database.engine)
    with identity_database.transaction() as repositories:
        repositories.accounts.add(
            AccountFaker.fake(
                id=ACCOUNT_ID,
                email='streak-preference-read@example.test',
                access_version=1,
            )
        )
        repositories.accounts.add(
            AccountFaker.fake(
                id=OTHER_ACCOUNT_ID,
                email='other-streak-preference-read@example.test',
                access_version=1,
            )
        )
    application.state.authentication_provider = _TestAuthenticationProvider()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetStreakReminderPreferenceController:
    def test_should_default_to_off_for_a_new_account(self, client: TestClient) -> None:
        response = client.get(PATH, headers=FIRST_USER)

        assert response.status_code == 200
        assert response.json() == {'enabled': False}

    def test_should_return_the_stored_preference_of_the_caller_only(
        self, client: TestClient
    ) -> None:
        client.put(PATH, json={'enabled': True}, headers=FIRST_USER)

        first = client.get(PATH, headers=FIRST_USER)
        second = client.get(PATH, headers=SECOND_USER)

        assert first.json() == {'enabled': True}
        assert second.json() == {'enabled': False}

    def test_should_return_401_without_a_session(self, client: TestClient) -> None:
        response = client.get(PATH)

        assert response.status_code == 401

    def test_should_return_401_for_an_invalid_token(self, client: TestClient) -> None:
        response = client.get(PATH, headers={'Authorization': 'Bearer unknown-token'})

        assert response.status_code == 401
