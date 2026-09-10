from fastapi import FastAPI, APIRouter

from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.rest.router import LearningRouter
from shifu.shared.rest.router import SharedRouter


def create_app() -> FastAPI:
    app = FastAPI(
        title='Shifu API',
        version='0.1.0',
    )
    router = APIRouter()

    router.include_router(SharedRouter.register())
    router.include_router(IdentityRouter.register())
    router.include_router(CurriculumRouter.register())
    router.include_router(LearningRouter.register())
    router.include_router(GamificationRouter.register())
    router.include_router(IntelligenceRouter.register())

    app.include_router(router.register())

    return app


app = create_app()

__all__ = ['app', 'create_app']
