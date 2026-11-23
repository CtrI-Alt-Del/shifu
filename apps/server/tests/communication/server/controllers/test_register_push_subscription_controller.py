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
PATH = '/communication/push-subscriptions'
ENDPOINT = 'https://fcm.googleapis.com/fcm/send/browser-one'
FIRST_KEYS = {'p256dh': 'first-p256dh-key', 'auth': 'first-auth-value'}
SECOND_KEYS = {'p256dh': 'second-p256dh-key', 'auth': 'second-auth-value'}
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
                email='push-subscription@example.test',
                access_version=1,
            )
        )
        repositories.accounts.add(
            AccountFaker.fake(
                id=OTHER_ACCOUNT_ID,
                email='other-push-subscription@example.test',
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


def _body(
    endpoint: str = ENDPOINT, keys: dict[str, str] | None = None
) -> dict[str, object]:
    return {'endpoint': endpoint, 'keys': keys or FIRST_KEYS}


class TestRegisterPushSubscriptionController:
    def test_should_register_the_browser_for_the_caller(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        response = client.put(PATH, json=_body(), headers=FIRST_USER)

        assert response.status_code == 204
        assert response.content == b''
        with database.transaction() as repositories:
            stored = repositories.push_subscriptions.find_many_by_account_id(ACCOUNT_ID)
            assert len(stored) == 1
            assert stored[0].endpoint == ENDPOINT
            assert stored[0].p256dh_key == FIRST_KEYS['p256dh']
            assert stored[0].auth_secret == FIRST_KEYS['auth']
            assert (
                repositories.push_subscriptions.find_many_by_account_id(
                    OTHER_ACCOUNT_ID
                )
                == ()
            )

    def test_should_keep_a_single_row_when_the_same_account_registers_again(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        client.put(PATH, json=_body(), headers=FIRST_USER)

        response = client.put(PATH, json=_body(keys=SECOND_KEYS), headers=FIRST_USER)

        assert response.status_code == 204
        with database.transaction() as repositories:
            stored = repositories.push_subscriptions.find_many_by_account_id(ACCOUNT_ID)
            assert len(stored) == 1
            assert stored[0].p256dh_key == SECOND_KEYS['p256dh']
            assert stored[0].auth_secret == SECOND_KEYS['auth']

    def test_should_relink_an_endpoint_to_the_latest_caller(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        client.put(PATH, json=_body(), headers=FIRST_USER)

        response = client.put(PATH, json=_body(keys=SECOND_KEYS), headers=SECOND_USER)

        assert response.status_code == 204
        with database.transaction() as repositories:
            assert (
                repositories.push_subscriptions.find_many_by_account_id(ACCOUNT_ID)
                == ()
            )
            moved = repositories.push_subscriptions.find_many_by_account_id(
                OTHER_ACCOUNT_ID
            )
            assert len(moved) == 1
            assert moved[0].endpoint == ENDPOINT
            assert moved[0].p256dh_key == SECOND_KEYS['p256dh']

    def test_should_return_401_without_a_session(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        response = client.put(PATH, json=_body())

        assert response.status_code == 401
        with database.transaction() as repositories:
            assert repositories.push_subscriptions.find_by_endpoint(ENDPOINT) is None

    def test_should_return_401_for_an_invalid_token(self, client: TestClient) -> None:
        response = client.put(
            PATH,
            json=_body(),
            headers={'Authorization': 'Bearer unknown-token'},
        )

        assert response.status_code == 401

    @pytest.mark.parametrize(
        'payload',
        [
            _body(endpoint='http://fcm.googleapis.com/fcm/send/browser-one'),
            _body(endpoint='https://fcm.googleapis.com/' + 'a' * 2048),
            _body(endpoint='not-a-url'),
            _body(keys={'p256dh': '', 'auth': 'first-auth-value'}),
            _body(keys={'p256dh': 'first-p256dh-key', 'auth': ''}),
            _body(keys={'p256dh': '   ', 'auth': 'first-auth-value'}),
            {'endpoint': ENDPOINT},
            {'keys': FIRST_KEYS},
            {**_body(), 'unexpected': 'field'},
        ],
        ids=[
            'non-https-endpoint',
            'endpoint-over-limit',
            'endpoint-not-a-url',
            'empty-p256dh',
            'empty-auth',
            'blank-p256dh',
            'missing-keys',
            'missing-endpoint',
            'unknown-field',
        ],
    )
    def test_should_return_422_for_an_invalid_subscription_without_writing(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
        payload: dict[str, object],
    ) -> None:
        response = client.put(PATH, json=payload, headers=FIRST_USER)

        assert response.status_code == 422
        assert response.json() == {
            'code': 'validation_error',
            'message': 'Os dados enviados são inválidos.',
        }
        with database.transaction() as repositories:
            assert (
                repositories.push_subscriptions.find_many_by_account_id(ACCOUNT_ID)
                == ()
            )

    @pytest.mark.parametrize(
        'endpoint',
        [
            'https://fcm.googleapis.com/fcm/send/abc',
            'https://fcm.googleapis.com:443/fcm/send/abc',
            'https://updates.push.services.mozilla.com/wpush/v2/abc',
            'https://web.push.apple.com/abc',
            'https://db5p.notify.windows.com/w/?token=abc',
        ],
        ids=['fcm', 'fcm-explicit-port', 'mozilla', 'apple', 'windows'],
    )
    def test_should_accept_an_endpoint_of_each_trusted_push_service(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
        endpoint: str,
    ) -> None:
        response = client.put(PATH, json=_body(endpoint=endpoint), headers=FIRST_USER)

        assert response.status_code == 204
        with database.transaction() as repositories:
            assert (
                repositories.push_subscriptions.find_by_endpoint(endpoint) is not None
            )

    @pytest.mark.parametrize(
        'endpoint',
        [
            'https://push.example.test/send/abc',
            'https://fcm.googleapis.com.example.test/send/abc',
            'https://x.fcm.googleapis.com/send/abc',
            'https://push.apple.com/send/abc',
            'https://user:secret@fcm.googleapis.com/send/abc',
            'https://fcm.googleapis.com:8443/send/abc',
            'https://127.0.0.1/send/abc',
            'https://evil.example\\.push.apple.com/send/abc',
            'https://fcm.googleapis.com./send/abc',
            'https://fcm%2Egoogleapis.com/send/abc',
            'https://FCM.googleapis.com/send/abc',
            'https://evil.example#.push.apple.com/send/abc',
            'https://evil.example?.push.apple.com/send/abc',
        ],
        ids=[
            'unknown-host',
            'lookalike-suffix',
            'subdomain-of-an-exact-host',
            'apex-of-a-suffix-domain',
            'credentials',
            'other-port',
            'ip-literal',
            'backslash',
            'trailing-dot',
            'percent-encoded-host',
            'upper-case-host',
            'fragment-hides-the-host',
            'query-hides-the-host',
        ],
    )
    def test_should_return_422_for_an_endpoint_outside_the_trusted_push_services(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
        endpoint: str,
    ) -> None:
        response = client.put(PATH, json=_body(endpoint=endpoint), headers=FIRST_USER)

        assert response.status_code == 422
        assert response.json() == {
            'code': 'validation_error',
            'message': 'Não foi possível registrar este navegador para lembretes.',
        }
        with database.transaction() as repositories:
            assert repositories.push_subscriptions.find_by_endpoint(endpoint) is None
            assert (
                repositories.push_subscriptions.find_many_by_account_id(ACCOUNT_ID)
                == ()
            )

    @staticmethod
    def _register_at_the_same_time(
        client: TestClient,
        endpoint: str,
    ) -> tuple[int, int]:
        barrier = Barrier(2)

        def register(headers: dict[str, str], keys: dict[str, str]) -> int:
            barrier.wait(timeout=10)
            return client.put(
                PATH,
                json=_body(endpoint=endpoint, keys=keys),
                headers=headers,
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(register, FIRST_USER, FIRST_KEYS)
            second = executor.submit(register, SECOND_USER, SECOND_KEYS)
            return first.result(timeout=30), second.result(timeout=30)

    def test_should_accept_concurrent_first_registrations_of_the_same_endpoint(
        self,
        client: TestClient,
        database: SqlalchemyCommunicationDatabase,
    ) -> None:
        # Four rounds keep the 10-request rate limit bucket untouched.
        for round_number in range(4):
            endpoint = f'{ENDPOINT}-race-{round_number}'

            statuses = self._register_at_the_same_time(client, endpoint)

            assert statuses == (204, 204)
            with database.transaction() as repositories:
                owners = [
                    subscription.account_id
                    for account_id in (ACCOUNT_ID, OTHER_ACCOUNT_ID)
                    for subscription in repositories.push_subscriptions.find_many_by_account_id(
                        account_id
                    )
                    if subscription.endpoint == endpoint
                ]
            assert len(owners) == 1
