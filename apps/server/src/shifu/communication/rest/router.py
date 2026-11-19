from fastapi import APIRouter

from shifu.communication.rest.controllers import (
    ChangeStreakReminderPreferenceController,
    GetPushPublicKeyController,
    GetStreakReminderPreferenceController,
    RegisterPushSubscriptionController,
)


class CommunicationRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/communication', tags=['communication'])
        GetPushPublicKeyController.handle(router)
        RegisterPushSubscriptionController.handle(router)
        GetStreakReminderPreferenceController.handle(router)
        ChangeStreakReminderPreferenceController.handle(router)
        return router
