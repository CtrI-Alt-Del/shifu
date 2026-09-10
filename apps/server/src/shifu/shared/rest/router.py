from fastapi import APIRouter

from shifu.shared.rest.controllers.check_health_controller import CheckHealthController
from shifu.shared.rest.controllers.read_api_info_controller import ReadApiInfoController


class SharedRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(tags=["system"])
        ReadApiInfoController.handle(router)
        CheckHealthController.handle(router)
        return router


__all__ = ["SharedRouter"]
