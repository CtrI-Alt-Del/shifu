from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.rest.router import LearningRouter
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.providers.cache.redis.redis_cache_provider import (
    RedisCacheProvider,
)
from shifu.shared.rest.middlewares.rate_limit_middleware import RateLimitMiddleware
from shifu.shared.rest.router import SharedRouter
from shifu.shared.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    cache_provider = RedisCacheProvider.connect(settings.redis_url)

    try:
        await cache_provider.ping()
    except Exception as error:
        await cache_provider.close()
        raise ServiceUnavailableError(
            message='Redis is unavailable; the server cannot start.'
        ) from error

    app.state.cache_provider = cache_provider

    try:
        yield
    finally:
        await cache_provider.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title='Shifu API',
        version='0.1.0',
        lifespan=_lifespan,
    )
    router = APIRouter()

    router.include_router(SharedRouter.register())
    router.include_router(IdentityRouter.register())
    router.include_router(CurriculumRouter.register())
    router.include_router(LearningRouter.register())
    router.include_router(GamificationRouter.register())
    router.include_router(IntelligenceRouter.register())

    app.include_router(router)

    app.add_middleware(
        RateLimitMiddleware, trusted_proxy_ips=settings.trusted_proxy_ips
    )

    return app


app = create_app()
