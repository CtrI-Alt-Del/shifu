from datetime import datetime

from shifu.communication.core.domain.entities import PushSubscription
from shifu.communication.core.domain.errors import InvalidPushSubscriptionError
from shifu.communication.core.domain.structures import TrustedPushEndpoint
from shifu.communication.core.interfaces import CommunicationDatabase
from shifu.shared.core.interfaces import IdentifierProvider


class RegisterPushSubscriptionUseCase:
    """Link one browser endpoint to the caller, re-linking it when it moved."""

    def __init__(
        self,
        database: CommunicationDatabase,
        id_provider: IdentifierProvider,
    ) -> None:
        self._database = database
        self._id_provider = id_provider

    def execute(
        self,
        account_id: str,
        *,
        endpoint: str,
        p256dh_key: str,
        auth_secret: str,
        now: datetime,
    ) -> None:
        TrustedPushEndpoint.create(endpoint)
        with self._database.transaction() as repositories:
            subscription = repositories.push_subscriptions.find_by_endpoint(endpoint)
            if subscription is None:
                created = PushSubscription.create(
                    id=self._id_provider.generate(),
                    account_id=account_id,
                    endpoint=endpoint,
                    p256dh_key=p256dh_key,
                    auth_secret=auth_secret,
                    now=now,
                )
                if repositories.push_subscriptions.try_add(created):
                    return

                # A concurrent first registration won; link its row to the caller.
                subscription = repositories.push_subscriptions.find_by_endpoint(
                    endpoint
                )
                if subscription is None:
                    raise InvalidPushSubscriptionError

            subscription.relink(
                account_id=account_id,
                p256dh_key=p256dh_key,
                auth_secret=auth_secret,
                now=now,
            )
            repositories.push_subscriptions.update(subscription)
