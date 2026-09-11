from fastapi import APIRouter

from shifu.shared.rest.controllers.check_health_controller import CheckHealthController


class SharedRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(tags=['system'])
        CheckHealthController.handle(router)
        return router
