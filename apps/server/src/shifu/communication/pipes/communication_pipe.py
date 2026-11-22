from fastapi import Request

from shifu.communication.core.interfaces import (
    CommunicationDatabase,
    PushNotificationProvider,
)


class CommunicationPipe:
    @staticmethod
    def get_database(request: Request) -> CommunicationDatabase:
        return request.app.state.communication_database

    @staticmethod
    def get_push_notification_provider(
        request: Request,
    ) -> PushNotificationProvider | None:
        return request.app.state.push_notification_provider
