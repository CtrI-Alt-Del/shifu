from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine

from shifu.curriculum.rest.router import CurriculumRouter
from shifu.identity.messaging.inngest import IdentityInngestMessaging
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.rest.router import IdentityRouter
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.rest.router import LearningRouter
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.messaging.inngest import InngestBroker, InngestMessaging
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.rest.router import SharedRouter
from shifu.rest.handlers import AppErrorHandler


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
        identity_database = SqlalchemyIdentityDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
            broker = cast('InngestBroker', app.state.inngest_broker)
            broker.start()
            try:
                yield
            finally:
                broker.stop()
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
        FastAPIApp._register_routers(app)
        return app


app = FastAPIApp.register()
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine

from shifu.curriculum.rest.router import CurriculumRouter
from shifu.identity.messaging.inngest import IdentityInngestMessaging
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.rest.router import IdentityRouter
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.rest.router import LearningRouter
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.messaging.inngest import InngestBroker, InngestMessaging
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.rest.router import SharedRouter
from shifu.rest.handlers import AppErrorHandler


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
        identity_database = SqlalchemyIdentityDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
            broker = cast('InngestBroker', app.state.inngest_broker)
            broker.start()
            try:
                yield
            finally:
                broker.stop()
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
        FastAPIApp._register_routers(app)
        return app


app = FastAPIApp.register()
