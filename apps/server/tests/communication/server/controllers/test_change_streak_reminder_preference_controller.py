from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
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
                email='streak-preference@example.test',
                access_version=1,
            )
        )
        repositories.accounts.add(
            AccountFaker.fake(
                id=OTHER_ACCOUNT_ID,
                email='other-streak-preference@example.test',
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


@pytest.fixture
def database(postgres_database: PostgresDatabase) -> SqlalchemyCommunicationDatabase:
    return SqlalchemyCommunicationDatabase(postgres_database.engine)


class TestChangeStreakReminderPreferenceController:
    def test_should_turn_the_preference_on_and_persist_it(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        response = client.put(PATH, json={'enabled': True}, headers=FIRST_USER)

        assert response.status_code == 200
        assert response.json() == {'enabled': True}
        assert client.get(PATH, headers=FIRST_USER).json() == {'enabled': True}
        with database.transaction() as repositories:
            stored = repositories.streak_reminder_preferences.find_by_account_id(
                ACCOUNT_ID
            )
            assert stored is not None
            assert stored.enabled is True

    def test_should_turn_the_preference_back_off(self, client: TestClient) -> None:
        client.put(PATH, json={'enabled': True}, headers=FIRST_USER)

        response = client.put(PATH, json={'enabled': False}, headers=FIRST_USER)

        assert response.status_code == 200
        assert response.json() == {'enabled': False}
        assert client.get(PATH, headers=FIRST_USER).json() == {'enabled': False}

    def test_should_change_the_callers_preference_only(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        client.put(PATH, json={'enabled': True}, headers=FIRST_USER)

        assert client.get(PATH, headers=SECOND_USER).json() == {'enabled': False}
        with database.transaction() as repositories:
            assert (
                repositories.streak_reminder_preferences.find_by_account_id(
                    OTHER_ACCOUNT_ID
                )
                is None
            )

    def test_should_return_401_without_a_session(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        response = client.put(PATH, json={'enabled': True})

        assert response.status_code == 401
        with database.transaction() as repositories:
            assert (
                repositories.streak_reminder_preferences.find_by_account_id(ACCOUNT_ID)
                is None
            )

    @pytest.mark.parametrize(
        'payload',
        [
            {},
            {'enabled': 'yes'},
            {'enabled': 1},
            {'enabled': None},
            {'enabled': True, 'x': 1},
        ],
        ids=['missing', 'string', 'integer', 'null', 'unknown-field'],
    )
    def test_should_return_422_for_an_invalid_body_without_writing(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
        payload: dict[str, object],
    ) -> None:
        response = client.put(PATH, json=payload, headers=FIRST_USER)

        assert response.status_code == 422
        with database.transaction() as repositories:
            assert (
                repositories.streak_reminder_preferences.find_by_account_id(ACCOUNT_ID)
                is None
            )

    def test_should_accept_concurrent_first_changes_of_the_same_account(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        barrier = Barrier(2)

        def change(*, enabled: bool) -> int:
            barrier.wait(timeout=10)
            return client.put(
                PATH, json={'enabled': enabled}, headers=FIRST_USER
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(change, enabled=True)
            second = executor.submit(change, enabled=False)
            statuses = (first.result(timeout=30), second.result(timeout=30))

        assert statuses == (200, 200)
        with database.transaction() as repositories:
            stored = repositories.streak_reminder_preferences.find_by_account_id(
                ACCOUNT_ID
            )
        assert stored is not None
        assert client.get(PATH, headers=FIRST_USER).json() == {
            'enabled': stored.enabled
        }
