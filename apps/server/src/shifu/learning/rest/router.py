from fastapi import APIRouter

from shifu.learning.rest.controllers import (
    AddSkillToGoalController,
    CreateGoalController,
    GetDiagnosticController,
    GetGoalDetailController,
    GetMaterialController,
    GetChoiceActivityController,
    GetChoiceAttemptController,
    GetCompetencyDetailController,
    GetHomeGoalsController,
    ListAvailableSkillsController,
    RemoveGoalController,
    RetryChoiceEvaluationController,
    SearchSkillCatalogController,
    SubmitChoiceActivityController,
    StartSkillController,
)


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        ListAvailableSkillsController.handle(router)
        CreateGoalController.handle(router)
        GetCompetencyDetailController.handle(router)
        GetGoalDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        SearchSkillCatalogController.handle(router)
        AddSkillToGoalController.handle(router)
        RemoveGoalController.handle(router)
        StartSkillController.handle(router)
        GetDiagnosticController.handle(router)
        GetMaterialController.handle(router)
        GetChoiceActivityController.handle(router)
        SubmitChoiceActivityController.handle(router)
        GetChoiceAttemptController.handle(router)
        RetryChoiceEvaluationController.handle(router)
        return router
