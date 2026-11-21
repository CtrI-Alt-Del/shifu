from shifu.communication.core.domain.errors import PushUnavailableError
from shifu.communication.core.interfaces import PushNotificationProvider


class GetPushPublicKeyUseCase:
    """Expose the push public key only when push delivery is configured."""

    def __init__(
        self,
        push_notification_provider: PushNotificationProvider | None,
    ) -> None:
        self._push_notification_provider = push_notification_provider

    def execute(self) -> str:
        if self._push_notification_provider is None:
            raise PushUnavailableError
        return self._push_notification_provider.public_key
