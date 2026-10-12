from fastapi import APIRouter

from shifu.gamification.rest.controllers import ListAchievementsController


class GamificationRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/gamification', tags=['gamification'])
        ListAchievementsController.handle(router)
        return router
