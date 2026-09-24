from fastapi import APIRouter

<<<<<<< HEAD
from shifu.learning.rest.controllers import (
    AddSkillToGoalController,
    GetCompetencyDetailController,
    GetHomeGoalsController,
    SearchSkillCatalogController,
)
=======
from shifu.learning.rest.controllers import GetCompetencyDetailController
from shifu.learning.rest.controllers import GetGoalDetailController
from shifu.learning.rest.controllers import GetHomeGoalsController
>>>>>>> origin/main


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        GetGoalDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        SearchSkillCatalogController.handle(router)
        AddSkillToGoalController.handle(router)
        return router
