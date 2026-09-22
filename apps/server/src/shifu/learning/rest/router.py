from fastapi import APIRouter

from shifu.learning.rest.controllers import GetCompetencyDetailController


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        return router
