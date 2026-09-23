from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import CurriculumCatalogReaderProvider
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.messaging.inngest import IdentityInngestMessaging
from shifu.identity.providers.auth.jwt.jwks.jwks_jwt_authentication_provider import (
    JwksJwtAuthenticationProvider,
)
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.rest.router import LearningRouter
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.messaging.inngest import InngestBroker, InngestMessaging
from shifu.shared.providers.cache.redis.redis_cache_provider import (
    RedisCacheProvider,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.rest.middlewares.rate_limit_middleware import RateLimitMiddleware
from shifu.shared.rest.router import SharedRouter
from shifu.shared.settings import get_settings


class FastAPIApp:
    @staticmethod
    def _register_routers(app: FastAPI) -> None:
        router = APIRouter()
        router.include_router(SharedRouter.register())
        router.include_router(IdentityRouter.register())
        router.include_router(CurriculumRouter.register())
        router.include_router(LearningRouter.register())
        router.include_router(GamificationRouter.register())
        router.include_router(IntelligenceRouter.register())
        app.include_router(router)

    @staticmethod
    def register(database_engine: Engine | None = None) -> FastAPI:
        database_engine = database_engine or Session.create_database_engine()
        id_provider = SystemIdentifierProvider()
        settings = get_settings()
        identity_database = SqlalchemyIdentityDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        curriculum_database = SqlalchemyCurriculumDatabase(engine=database_engine)
        learning_database = SqlalchemyLearningDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        curriculum_content_provider = DatabaseCurriculumContentProvider(
            curriculum_database
        )
        curriculum_catalog_reader = CurriculumCatalogReaderProvider(curriculum_database)
        authentication_provider = JwksJwtAuthenticationProvider(
            identity_database=identity_database,
            jwks_url=ENVIRONMENT.auth_jwks_url,
            issuer=ENVIRONMENT.auth_issuer,
            audience=ENVIRONMENT.auth_audience,
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
            cache_provider = RedisCacheProvider.connect(settings.redis_url)
            try:
                await cache_provider.ping()
            except Exception as error:
                await cache_provider.close()
                database_engine.dispose()
                raise ServiceUnavailableError(
                    message='O Redis está indisponível; o servidor não pode iniciar.'
                ) from error

            app.state.cache_provider = cache_provider
            broker = cast('InngestBroker', app.state.inngest_broker)
            broker.start()
            try:
                yield
            finally:
                broker.stop()
                await cache_provider.close()
                database_engine.dispose()

        app = FastAPI(title='Shifu API', version='0.1.0', lifespan=lifespan)
        inngest_client = InngestMessaging.register(
            app,
            job_group_registrars=[IdentityInngestMessaging.register_jobs],
        )
        app.state.inngest_broker = InngestBroker(
            inngest_client,
            engine=database_engine,
            id_provider=id_provider,
        )
        AppErrorHandler.register(app)
        app.state.identity_database = identity_database
        app.state.authentication_provider = authentication_provider
        app.state.identifier_provider = id_provider
        app.state.learning_database = learning_database
        app.state.curriculum_database = curriculum_database
        app.state.curriculum_content_provider = curriculum_content_provider
        app.state.curriculum_catalog_reader = curriculum_catalog_reader
        app.state.intelligence_database = SqlalchemyIntelligenceDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        FastAPIApp._register_routers(app)
        app.add_middleware(
            RateLimitMiddleware,
            trusted_proxy_ips=settings.trusted_proxy_ips,
        )
        return app


app = FastAPIApp.register()
