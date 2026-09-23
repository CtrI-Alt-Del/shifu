from fastapi import APIRouter

from shifu.learning.rest.controllers import (
    AddSkillToGoalController,
    GetCompetencyDetailController,
    GetHomeGoalsController,
    SearchSkillCatalogController,
)


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        SearchSkillCatalogController.handle(router)
        AddSkillToGoalController.handle(router)
        return router
