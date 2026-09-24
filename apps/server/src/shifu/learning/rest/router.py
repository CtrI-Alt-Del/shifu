from fastapi import APIRouter

from shifu.learning.rest.controllers import GetCompetencyDetailController
from shifu.learning.rest.controllers import GetGoalDetailController
from shifu.learning.rest.controllers import GetHomeGoalsController


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        GetGoalDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        return router
