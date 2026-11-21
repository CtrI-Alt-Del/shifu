import base64
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from shifu.app import FastAPIApp
from shifu.communication.providers.push import PywebpushPushNotificationProvider
from shifu.shared.constants import EnvironmentSettings
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.push_service_stub_fixture import PushVapidKeys
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
PATH = '/communication/push-subscriptions/public-key'
AUTHORIZATION = {'Authorization': 'Bearer test-access-token'}


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
    push_vapid_keys: PushVapidKeys,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(
        postgres_database.engine,
        push_notification_provider=PywebpushPushNotificationProvider(
            vapid_private_key=push_vapid_keys.private_key,
            vapid_public_key=push_vapid_keys.public_key,
            subject=push_vapid_keys.subject,
            timeout_seconds=5,
        ),
    )
    application.state.authentication_provider = _TestAuthenticationProvider()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetPushPublicKeyController:
    def test_should_return_the_configured_public_key_and_nothing_else(
        self,
        client: TestClient,
        push_vapid_keys: PushVapidKeys,
    ) -> None:
        response = client.get(PATH, headers=AUTHORIZATION)

        assert response.status_code == 200
        assert response.json() == {'publicKey': push_vapid_keys.public_key}
        assert push_vapid_keys.private_key not in response.text

    def test_should_return_503_when_push_is_not_configured(
        self,
        application: FastAPI,
        client: TestClient,
        push_vapid_keys: PushVapidKeys,
    ) -> None:
        application.state.push_notification_provider = None

        response = client.get(PATH, headers=AUTHORIZATION)

        assert response.status_code == 503
        assert response.json() == {
            'code': 'push_unavailable',
            'message': 'Os lembretes por notificação estão indisponíveis no momento.',
        }
        assert push_vapid_keys.public_key not in response.text

    def test_should_return_401_without_a_session(self, client: TestClient) -> None:
        response = client.get(PATH)

        assert response.status_code == 401

    def test_should_return_401_for_an_invalid_token(self, client: TestClient) -> None:
        response = client.get(PATH, headers={'Authorization': 'Bearer other-token'})

        assert response.status_code == 401


class TestPushConfigurationProof:
    """Configuration proof, not HTTP proof (CA-22).

    `ENVIRONMENT` is built when `shared/constants/environment.py` loads, before
    the application serves, so an unconfigured staging process fails at import.
    The same validation is asserted here through the public settings factory.
    """

    PRIVATE_KEY = 'private-key-value-that-must-never-be-echoed'
    PUBLIC_KEY = 'public-key-value-that-must-never-be-echoed'

    @staticmethod
    def _staging_environment() -> dict[str, str]:
        return {
            'SHIFU_SERVER_APP_MODE': 'staging',
            'SHIFU_RELEASE_VERSION': '2026.11.18',
            'SHIFU_COMMUNICATION_ENCRYPTION_KEYS': (
                'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
            ),
            'SHIFU_EMAIL_PROVIDER': 'resend',
            'SHIFU_RESEND_API_KEY': 're_test_key',
            'SHIFU_RESEND_FROM': 'Shifu <no-reply@shifu.local>',
        }

    def test_should_refuse_staging_without_the_push_keys(self) -> None:
        with pytest.raises(ValidationError) as error:
            EnvironmentSettings.from_environment(self._staging_environment())

        assert 'VAPID keys are required' in str(error.value)

    def test_should_refuse_staging_without_the_push_subject(self) -> None:
        environment = {
            **self._staging_environment(),
            'SHIFU_WEB_PUSH_VAPID_PRIVATE_KEY': self.PRIVATE_KEY,
            'SHIFU_WEB_PUSH_VAPID_PUBLIC_KEY': self.PUBLIC_KEY,
        }

        with pytest.raises(ValidationError) as error:
            EnvironmentSettings.from_environment(environment)

        message = str(error.value)
        assert 'subject is required' in message
        assert self.PRIVATE_KEY not in message
        assert self.PUBLIC_KEY not in message

    def test_should_start_staging_with_the_keys_and_subject(self) -> None:
        settings = EnvironmentSettings.from_environment(
            {
                **self._staging_environment(),
                'SHIFU_WEB_PUSH_VAPID_PRIVATE_KEY': self.PRIVATE_KEY,
                'SHIFU_WEB_PUSH_VAPID_PUBLIC_KEY': self.PUBLIC_KEY,
                'SHIFU_WEB_PUSH_SUBJECT': 'mailto:push@shifu.local',
            }
        )

        assert settings.web_push_vapid_public_key == self.PUBLIC_KEY
        assert settings.web_push_subject == 'mailto:push@shifu.local'

    @staticmethod
    def _another_private_key() -> str:
        private_value = ec.generate_private_key(ec.SECP256R1()).private_numbers()
        encoded = base64.urlsafe_b64encode(
            private_value.private_value.to_bytes(32, 'big')
        )
        return encoded.rstrip(b'=').decode()

    def test_should_refuse_a_private_key_that_does_not_match_the_public_key(
        self,
        push_vapid_keys: PushVapidKeys,
    ) -> None:
        other_keys = PushVapidKeys(
            private_key=self._another_private_key(),
            public_key=push_vapid_keys.public_key,
            subject=push_vapid_keys.subject,
        )

        with pytest.raises(ValueError, match='does not match the public key') as error:
            PywebpushPushNotificationProvider(
                vapid_private_key=other_keys.private_key,
                vapid_public_key=other_keys.public_key,
                subject=other_keys.subject,
                timeout_seconds=5,
            )

        assert other_keys.private_key not in str(error.value)
        assert other_keys.public_key not in str(error.value)

    def test_should_accept_the_matching_pair_with_or_without_padding(
        self,
        push_vapid_keys: PushVapidKeys,
    ) -> None:
        provider = PywebpushPushNotificationProvider(
            vapid_private_key=push_vapid_keys.private_key,
            vapid_public_key=push_vapid_keys.public_key + '=',
            subject=push_vapid_keys.subject,
            timeout_seconds=5,
        )

        assert provider.public_key.rstrip('=') == push_vapid_keys.public_key
