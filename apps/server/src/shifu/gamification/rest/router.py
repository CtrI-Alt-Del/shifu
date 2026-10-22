from fastapi import APIRouter

from shifu.gamification.rest.controllers import (
    GetGamificationOverviewController,
    GetPracticeCalendarController,
    GetXpHistoryController,
    ListAchievementsController,
)


class GamificationRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/gamification', tags=['gamification'])
        GetGamificationOverviewController.handle(router)
        ListAchievementsController.handle(router)
        GetPracticeCalendarController.handle(router)
        GetXpHistoryController.handle(router)
        return router
