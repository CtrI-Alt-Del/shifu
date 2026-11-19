import base64
import json
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, cast

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import (
    WebPushException,
    webpush,  # pyright: ignore[reportUnknownVariableType]
)
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.core.domain.structures import (
    PushDeliveryOutcome,
    StreakReminderMessage,
)


if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric import ec


class PywebpushPushNotificationProvider:
    """Send encrypted Web Push messages signed with the server VAPID key.

    Outcomes carry short codes only. The endpoint, the encryption keys and the
    payload are never returned, raised or logged by this adapter.
    """

    _ACCEPTED_MAX_STATUS: ClassVar[int] = HTTPStatus.ACCEPTED
    _GONE_STATUSES: ClassVar[frozenset[int]] = frozenset(
        {HTTPStatus.NOT_FOUND, HTTPStatus.GONE}
    )
    _TEMPORARY_STATUSES: ClassVar[frozenset[int]] = frozenset(
        {HTTPStatus.TOO_MANY_REQUESTS}
    )

    def __init__(
        self,
        vapid_private_key: str,
        vapid_public_key: str,
        subject: str,
        timeout_seconds: float,
    ) -> None:
        self._vapid = Vapid.from_string(  # pyright: ignore[reportUnknownMemberType]
            vapid_private_key
        )
        if self._derive_public_key(self._vapid) != vapid_public_key.rstrip('='):
            raise ValueError(
                'The web push VAPID private key does not match the public key'
            )
        self._public_key = vapid_public_key
        self._subject = subject
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _derive_public_key(vapid: Vapid) -> str:
        public_key = cast(
            'ec.EllipticCurvePublicKey | None',
            vapid.public_key,  # pyright: ignore[reportUnknownMemberType]
        )
        if public_key is None:
            raise ValueError('The web push VAPID private key is not valid')
        public_bytes = public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        return base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode()

    @property
    def public_key(self) -> str:
        return self._public_key

    def send(
        self,
        message: StreakReminderMessage,
        subscription: PushSubscription,
        *,
        ttl_seconds: int,
    ) -> PushDeliveryOutcome:
        payload = json.dumps(
            {
                'title': message.title,
                'body': message.body,
                'url': message.url,
                'tag': message.tag,
            },
            ensure_ascii=False,
        )
        try:
            response = webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh_key,
                        'auth': subscription.auth_secret,
                    },
                },
                data=payload,
                vapid_private_key=self._vapid,
                vapid_claims={'sub': self._subject},
                ttl=ttl_seconds,
                timeout=self._timeout_seconds,
            )
        except WebPushException as error:
            return self._outcome_for_status(error.status_code)
        except Timeout:
            return PushDeliveryOutcome.temporary_failure('timeout')
        except RequestsConnectionError:
            return PushDeliveryOutcome.temporary_failure('connection_error')
        except RequestException:
            return PushDeliveryOutcome.permanent_failure('request_invalid')
        except (ValueError, TypeError, IndexError, KeyError):
            return PushDeliveryOutcome.permanent_failure('subscription_invalid')

        status_code = getattr(response, 'status_code', None)
        if isinstance(status_code, int) and status_code <= self._ACCEPTED_MAX_STATUS:
            return PushDeliveryOutcome.accepted()
        return self._outcome_for_status(status_code)

    @classmethod
    def _outcome_for_status(cls, status_code: int | None) -> PushDeliveryOutcome:
        if status_code is None:
            return PushDeliveryOutcome.permanent_failure('subscription_invalid')
        if status_code in cls._GONE_STATUSES:
            return PushDeliveryOutcome.gone()
        if status_code in cls._TEMPORARY_STATUSES or status_code >= 500:
            return PushDeliveryOutcome.temporary_failure(f'http_{status_code}')
        return PushDeliveryOutcome.permanent_failure(f'http_{status_code}')
