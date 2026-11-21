from unittest.mock import create_autospec

import pytest

from shifu.communication.core.domain.errors import PushUnavailableError
from shifu.communication.core.interfaces import PushNotificationProvider
from shifu.communication.core.use_cases import GetPushPublicKeyUseCase


class TestGetPushPublicKeyUseCase:
    PUBLIC_KEY = 'BPublicKeyBase64Url'

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.push_notification_provider = create_autospec(
            PushNotificationProvider,
            instance=True,
        )
        self.push_notification_provider.public_key = self.PUBLIC_KEY

    def test_should_return_the_configured_public_key(self) -> None:
        subject = GetPushPublicKeyUseCase(self.push_notification_provider)

        assert subject.execute() == self.PUBLIC_KEY

    def test_should_raise_push_unavailable_when_push_is_not_configured(self) -> None:
        subject = GetPushPublicKeyUseCase(None)

        with pytest.raises(PushUnavailableError) as error:
            subject.execute()

        assert error.value.message == (
            'Os lembretes por notificação estão indisponíveis no momento.'
        )
