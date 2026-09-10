from fastapi import APIRouter

from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.rest.router import LearningRouter
from shifu.shared.rest.router import SharedRouter


class AppRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter()

        router.include_router(SharedRouter.register())
        router.include_router(IdentityRouter.register())
        router.include_router(CurriculumRouter.register())
        router.include_router(LearningRouter.register())
        router.include_router(GamificationRouter.register())
        router.include_router(IntelligenceRouter.register())

        return router


__all__ = ["AppRouter"]
