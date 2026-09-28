from fastapi import APIRouter

from shifu.learning.rest.controllers import (
    AbandonDiagnosticController,
    AddSkillToGoalController,
    CreateGoalController,
    GetChoiceActivityController,
    CompleteDiagnosticController,
    GetChoiceAttemptController,
    GetCompetencyDetailController,
    GetDiagnosticController,
    GetGoalDetailController,
    GetHomeGoalsController,
    GetMaterialController,
    GetMaterialDetailController,
    GetSkillExperienceDetailController,
    ListAvailableSkillsController,
    RemoveGoalController,
    RemoveSkillFromGoalController,
    RetryChoiceEvaluationController,
    SearchSkillCatalogController,
    StartSkillController,
    SubmitChoiceActivityController,
    SubmitDiagnosticBatchController,
    PreviewActivityQuestionFeedbackController,
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
        GetMaterialDetailController.handle(router)
        SearchSkillCatalogController.handle(router)
        AddSkillToGoalController.handle(router)
        RemoveGoalController.handle(router)
        RemoveSkillFromGoalController.handle(router)
        StartSkillController.handle(router)
        AbandonDiagnosticController.handle(router)
        CompleteDiagnosticController.handle(router)
        GetDiagnosticController.handle(router)
        GetMaterialController.handle(router)
        GetChoiceActivityController.handle(router)
        PreviewActivityQuestionFeedbackController.handle(router)
        SubmitChoiceActivityController.handle(router)
        SubmitDiagnosticBatchController.handle(router)
        GetChoiceAttemptController.handle(router)
        RetryChoiceEvaluationController.handle(router)
        GetSkillExperienceDetailController.handle(router)
        return router
