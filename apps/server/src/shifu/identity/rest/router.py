from fastapi import APIRouter

from shifu.identity.rest.controllers.get_current_session_controller import (
    GetCurrentSessionController,
)
from shifu.identity.rest.controllers.main_page_entered_controller import (
    MainPageEnteredController,
)
from shifu.identity.rest.controllers.sign_in_controller import SignInController


class IdentityRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/identity', tags=['identity'])
        SignInController.handle(router)
        GetCurrentSessionController.handle(router)
        MainPageEnteredController.handle(router)
        return router
