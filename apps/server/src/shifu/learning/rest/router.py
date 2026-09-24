from fastapi import APIRouter

from shifu.learning.rest.controllers import GetCompetencyDetailController
from shifu.learning.rest.controllers import GetHomeGoalsController
from shifu.learning.rest.controllers import GetMaterialDetailController


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        GetMaterialDetailController.handle(router)
        return router
