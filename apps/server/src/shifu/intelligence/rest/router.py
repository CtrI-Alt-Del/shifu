from fastapi import APIRouter

from shifu.intelligence.rest.controllers.start_planning_controller import (
    StartPlanningController,
)


class IntelligenceRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/intelligence', tags=['intelligence'])
        StartPlanningController.handle(router)
        return router
