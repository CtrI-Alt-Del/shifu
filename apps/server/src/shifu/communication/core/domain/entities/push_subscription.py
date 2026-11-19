from datetime import datetime
from typing import ClassVar
from urllib.parse import urlsplit

from shifu.communication.core.domain.errors import InvalidPushSubscriptionError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class PushSubscription:
    MAX_ENDPOINT_LENGTH: ClassVar[int] = 2048
    MAX_KEY_LENGTH: ClassVar[int] = 255

    id: str
    account_id: str
    endpoint: str
    p256dh_key: str
    auth_secret: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidPushSubscriptionError)
        NonEmptyText.create(self.account_id, error_type=InvalidPushSubscriptionError)
        self._validate_endpoint(self.endpoint)
        self._validate_key(self.p256dh_key)
        self._validate_key(self.auth_secret)

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        endpoint: str,
        p256dh_key: str,
        auth_secret: str,
        now: datetime,
    ) -> 'PushSubscription':
        return cls(
            id=id,
            account_id=account_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_secret=auth_secret,
            created_at=now,
            updated_at=now,
        )

    def relink(
        self,
        *,
        account_id: str,
        p256dh_key: str,
        auth_secret: str,
        now: datetime,
    ) -> None:
        NonEmptyText.create(account_id, error_type=InvalidPushSubscriptionError)
        self._validate_key(p256dh_key)
        self._validate_key(auth_secret)
        self.account_id = account_id
        self.p256dh_key = p256dh_key
        self.auth_secret = auth_secret
        self.updated_at = now

    @classmethod
    def _validate_endpoint(cls, endpoint: str) -> None:
        if (
            type(endpoint) is not str
            or not 0 < len(endpoint) <= cls.MAX_ENDPOINT_LENGTH
        ):
            raise InvalidPushSubscriptionError
        if endpoint != endpoint.strip() or any(
            character.isspace() or ord(character) < 33 for character in endpoint
        ):
            raise InvalidPushSubscriptionError
        try:
            parts = urlsplit(endpoint)
            hostname = parts.hostname
        except ValueError:
            raise InvalidPushSubscriptionError from None
        if parts.scheme not in {'http', 'https'} or not hostname:
            raise InvalidPushSubscriptionError

    @classmethod
    def _validate_key(cls, key: str) -> None:
        if type(key) is not str or not key.strip() or len(key) > cls.MAX_KEY_LENGTH:
            raise InvalidPushSubscriptionError
