from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.core.domain.errors import InvalidPushSubscriptionError
from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    CommunicationDatabaseRepositories,
)
from shifu.communication.core.use_cases import RegisterPushSubscriptionUseCase
from shifu.fakers.communication.entities import PushSubscriptionFaker
from shifu.shared.core.interfaces import IdentifierProvider


class TestRegisterPushSubscriptionUseCase:
    ACCOUNT_ID = '01JACCOUNT000000000000000001'
    OTHER_ACCOUNT_ID = '01JACCOUNT000000000000000002'
    SUBSCRIPTION_ID = '01JSUBSCRIPTION00000000000001'
    ENDPOINT = 'https://fcm.googleapis.com/fcm/send/abc'
    P256DH_KEY = 'p256dh-key'
    AUTH_VALUE = 'auth-value'
    NEW_AUTH_VALUE = 'new-auth-value'

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(CommunicationDatabase, instance=True)
        self.repositories = create_autospec(
            CommunicationDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.id_provider = create_autospec(IdentifierProvider, instance=True)
        self.id_provider.generate.return_value = self.SUBSCRIPTION_ID
        self.now = datetime(2026, 11, 18, 21, 0, tzinfo=UTC)
        self.repositories.push_subscriptions.find_by_endpoint.return_value = None
        self.repositories.push_subscriptions.try_add.return_value = True
        self.subject = RegisterPushSubscriptionUseCase(self.database, self.id_provider)

    def test_should_create_a_subscription_linked_to_the_caller(self) -> None:
        self.subject.execute(
            self.ACCOUNT_ID,
            endpoint=self.ENDPOINT,
            p256dh_key=self.P256DH_KEY,
            auth_secret=self.AUTH_VALUE,
            now=self.now,
        )

        added = self.repositories.push_subscriptions.try_add.call_args.args[0]
        assert isinstance(added, PushSubscription)
        assert added.id == self.SUBSCRIPTION_ID
        assert added.account_id == self.ACCOUNT_ID
        assert added.endpoint == self.ENDPOINT
        assert added.p256dh_key == self.P256DH_KEY
        assert added.auth_secret == self.AUTH_VALUE
        assert added.created_at == self.now
        assert added.updated_at == self.now
        self.repositories.push_subscriptions.update.assert_not_called()

    def test_should_relink_an_endpoint_registered_by_another_account(self) -> None:
        existing = PushSubscriptionFaker.fake(
            id=self.SUBSCRIPTION_ID,
            account_id=self.OTHER_ACCOUNT_ID,
            endpoint=self.ENDPOINT,
            p256dh_key='old-p256dh',
            auth_secret=self.AUTH_VALUE,
            created_at=datetime(2026, 11, 1, tzinfo=UTC),
        )
        self.repositories.push_subscriptions.find_by_endpoint.return_value = existing

        self.subject.execute(
            self.ACCOUNT_ID,
            endpoint=self.ENDPOINT,
            p256dh_key='new-p256dh',
            auth_secret=self.NEW_AUTH_VALUE,
            now=self.now,
        )

        self.repositories.push_subscriptions.update.assert_called_once_with(existing)
        self.repositories.push_subscriptions.try_add.assert_not_called()
        assert existing.account_id == self.ACCOUNT_ID
        assert existing.p256dh_key == 'new-p256dh'
        assert existing.auth_secret == self.NEW_AUTH_VALUE
        assert existing.created_at == datetime(2026, 11, 1, tzinfo=UTC)
        assert existing.updated_at == self.now

    @pytest.mark.parametrize(
        'endpoint',
        [
            'not-a-url',
            'ftp://fcm.googleapis.com/fcm/send/abc',
            'https://',
            'https://fcm.googleapis.com/' + 'a' * 2048,
            'https://fcm.googleapis.com/send with spaces',
            '',
        ],
    )
    def test_should_reject_an_invalid_endpoint_without_writing(
        self, endpoint: str
    ) -> None:
        with pytest.raises(InvalidPushSubscriptionError):
            self.subject.execute(
                self.ACCOUNT_ID,
                endpoint=endpoint,
                p256dh_key=self.P256DH_KEY,
                auth_secret=self.AUTH_VALUE,
                now=self.now,
            )

        self.repositories.push_subscriptions.try_add.assert_not_called()
        self.repositories.push_subscriptions.update.assert_not_called()

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
        self, endpoint: str
    ) -> None:
        self.subject.execute(
            self.ACCOUNT_ID,
            endpoint=endpoint,
            p256dh_key=self.P256DH_KEY,
            auth_secret=self.AUTH_VALUE,
            now=self.now,
        )

        added = self.repositories.push_subscriptions.try_add.call_args.args[0]
        assert added.endpoint == endpoint

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
    def test_should_reject_an_endpoint_outside_the_trusted_push_services_without_writing(
        self, endpoint: str
    ) -> None:
        with pytest.raises(InvalidPushSubscriptionError):
            self.subject.execute(
                self.ACCOUNT_ID,
                endpoint=endpoint,
                p256dh_key=self.P256DH_KEY,
                auth_secret=self.AUTH_VALUE,
                now=self.now,
            )

        self.database.transaction.assert_not_called()
        self.repositories.push_subscriptions.try_add.assert_not_called()
        self.repositories.push_subscriptions.update.assert_not_called()

    @pytest.mark.parametrize(
        ('p256dh_key', 'auth_secret'),
        [
            ('', 'auth-secret'),
            ('p256dh-key', ''),
            ('   ', 'auth-secret'),
            ('k' * 256, 'a'),
        ],
    )
    def test_should_reject_empty_or_oversized_keys_without_writing(
        self, p256dh_key: str, auth_secret: str
    ) -> None:
        with pytest.raises(InvalidPushSubscriptionError):
            self.subject.execute(
                self.ACCOUNT_ID,
                endpoint=self.ENDPOINT,
                p256dh_key=p256dh_key,
                auth_secret=auth_secret,
                now=self.now,
            )

        self.repositories.push_subscriptions.try_add.assert_not_called()

    def test_should_not_relink_when_the_new_keys_are_invalid(self) -> None:
        existing = PushSubscriptionFaker.fake(
            account_id=self.OTHER_ACCOUNT_ID,
            endpoint=self.ENDPOINT,
        )
        self.repositories.push_subscriptions.find_by_endpoint.return_value = existing

        with pytest.raises(InvalidPushSubscriptionError):
            self.subject.execute(
                self.ACCOUNT_ID,
                endpoint=self.ENDPOINT,
                p256dh_key='',
                auth_secret=self.AUTH_VALUE,
                now=self.now,
            )

        assert existing.account_id == self.OTHER_ACCOUNT_ID
        self.repositories.push_subscriptions.update.assert_not_called()

    def test_should_relink_the_row_created_by_a_concurrent_first_registration(
        self,
    ) -> None:
        winner = PushSubscriptionFaker.fake(
            id='01JSUBSCRIPTION00000000000009',
            account_id=self.OTHER_ACCOUNT_ID,
            endpoint=self.ENDPOINT,
        )
        self.repositories.push_subscriptions.find_by_endpoint.side_effect = [
            None,
            winner,
        ]
        self.repositories.push_subscriptions.try_add.return_value = False

        self.subject.execute(
            self.ACCOUNT_ID,
            endpoint=self.ENDPOINT,
            p256dh_key=self.P256DH_KEY,
            auth_secret=self.NEW_AUTH_VALUE,
            now=self.now,
        )

        self.repositories.push_subscriptions.try_add.assert_called_once()
        self.repositories.push_subscriptions.update.assert_called_once_with(winner)
        assert winner.account_id == self.ACCOUNT_ID
        assert winner.auth_secret == self.NEW_AUTH_VALUE
        assert winner.updated_at == self.now

    def test_should_fail_safely_when_the_conflicting_row_cannot_be_found(self) -> None:
        self.repositories.push_subscriptions.find_by_endpoint.return_value = None
        self.repositories.push_subscriptions.try_add.return_value = False

        with pytest.raises(InvalidPushSubscriptionError):
            self.subject.execute(
                self.ACCOUNT_ID,
                endpoint=self.ENDPOINT,
                p256dh_key=self.P256DH_KEY,
                auth_secret=self.AUTH_VALUE,
                now=self.now,
            )

        self.repositories.push_subscriptions.update.assert_not_called()
