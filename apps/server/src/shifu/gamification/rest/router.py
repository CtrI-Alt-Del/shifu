from fastapi import APIRouter

from shifu.gamification.rest.controllers import (
    AnswerStreakReminderInviteController,
    ChangeStreakReminderHourController,
    GetActivityXpRewardController,
    GetGamificationOverviewController,
    GetPracticeCalendarController,
    GetStreakReminderController,
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
        GetActivityXpRewardController.handle(router)
        GetStreakReminderController.handle(router)
        ChangeStreakReminderHourController.handle(router)
        AnswerStreakReminderInviteController.handle(router)
        return router
