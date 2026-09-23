from fastapi import APIRouter

from shifu.learning.rest.controllers import (
    GetChoiceActivityController,
    GetChoiceAttemptController,
    GetCompetencyDetailController,
    GetHomeGoalsController,
    RetryChoiceEvaluationController,
    SubmitChoiceActivityController,
)


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        GetCompetencyDetailController.handle(router)
        GetHomeGoalsController.handle(router)
        GetChoiceActivityController.handle(router)
        SubmitChoiceActivityController.handle(router)
        GetChoiceAttemptController.handle(router)
        RetryChoiceEvaluationController.handle(router)
        return router
