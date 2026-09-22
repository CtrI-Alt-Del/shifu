from fastapi import APIRouter

from shifu.learning.rest.controllers.get_home_goals_controller import (
    GetHomeGoalsController,
)


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetHomeGoalsController.handle(router)
        return router
