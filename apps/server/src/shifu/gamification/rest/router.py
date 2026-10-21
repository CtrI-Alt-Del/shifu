from fastapi import APIRouter

from shifu.gamification.rest.controllers import (
    GetPracticeCalendarController,
    ListAchievementsController,
)


class GamificationRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/gamification', tags=['gamification'])
        ListAchievementsController.handle(router)
        GetPracticeCalendarController.handle(router)
        return router
