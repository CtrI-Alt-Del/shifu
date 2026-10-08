import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import httpx
from fastapi import APIRouter, FastAPI
from sqlalchemy import Engine
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shifu.communication.database.sqlalchemy import SqlalchemyCommunicationDatabase
from shifu.communication.messaging.inngest import CommunicationInngestMessaging
from shifu.composition import (
    PasswordRecoveryWorkflow,
    RegistrationConfirmationWorkflow,
    build_email_delivery_provider,
    build_message_renderer,
    build_secret_envelope_provider,
)
from shifu.curriculum.database.sqlalchemy import (
    SqlalchemyCurriculumDatabase,
)
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.messaging.inngest import GamificationInngestMessaging
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.messaging.inngest import IdentityInngestMessaging
from shifu.identity.providers.auth.jwt.jwks.jwks_jwt_authentication_provider import (
    JwksJwtAuthenticationProvider,
)
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.providers.code_rubric_assessor_provider.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.messaging.inngest import LearningInngestMessaging
from shifu.learning.rest.router import LearningRouter
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import CodeRubricAssessorProvider
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.messaging.inngest import InngestBroker, InngestMessaging
from shifu.shared.providers.cache.redis.redis_cache_provider import (
    RedisCacheProvider,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.rest.middlewares.rate_limit_middleware import RateLimitMiddleware
from shifu.shared.rest.router import SharedRouter
from shifu.shared.settings import get_settings


class ActivityPayloadLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self._app = app
        self._max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get('path', ''))
        if (
            scope['type'] != 'http'
            or scope.get('method') != 'POST'
            or not path.startswith('/learning/')
            or '/activities/' not in path
        ):
            await self._app(scope, receive, send)
            return

        buffered: list[Message] = []
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return

            if message['type'] != 'http.request':
                continue

            size += len(message.get('body', b''))
            if size > self._max_body_bytes:
                response = JSONResponse(
                    {'detail': 'A resposta enviada excede o limite permitido.'},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

            buffered.append(message)
            if not message.get('more_body', False):
                break

        async def replay_receive() -> Message:
            if buffered:
                return buffered.pop(0)

            return await receive()

        await self._app(scope, replay_receive, send)


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
        clock_provider = SystemClockProvider()
        settings = get_settings()
        identity_database = SqlalchemyIdentityDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        communication_database = SqlalchemyCommunicationDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        secret_envelope_provider = build_secret_envelope_provider(ENVIRONMENT)
        confirmation_workflow = RegistrationConfirmationWorkflow(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
            action_origin=ENVIRONMENT.confirmation_action_origin,
        )
        password_recovery_workflow = PasswordRecoveryWorkflow(
            communication_database=communication_database,
            id_provider=id_provider,
            clock_provider=clock_provider,
            secret_envelope_provider=secret_envelope_provider,
            action_origin=ENVIRONMENT.confirmation_action_origin,
        )
        message_renderer_provider = build_message_renderer()
        email_delivery_provider = build_email_delivery_provider(ENVIRONMENT)
        curriculum_database = SqlalchemyCurriculumDatabase(engine=database_engine)
        learning_database = SqlalchemyLearningDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        gamification_database = SqlalchemyGamificationDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        curriculum_content_provider = DatabaseCurriculumContentProvider(
            curriculum_database,
            diagnostic_revision_hmac_key=(
                settings.diagnostic_revision_hmac_key.get_secret_value().encode()
                if settings.diagnostic_revision_hmac_key is not None
                else None
            ),
        )
        curriculum_catalog_provider = DatabaseCurriculumCatalogProvider(
            curriculum_database
        )
        authentication_provider = JwksJwtAuthenticationProvider(
            identity_database=identity_database,
            jwks_url=ENVIRONMENT.auth_jwks_url,
            issuer=ENVIRONMENT.auth_issuer,
            audience=ENVIRONMENT.auth_audience,
        )

        def code_rubric_assessor_provider_factory() -> CodeRubricAssessorProvider:
            assessor = getattr(app.state, 'code_rubric_assessor_provider', None)
            if assessor is None:
                raise ServiceUnavailableError(
                    message='A avaliação de código está indisponível.'
                )

            return cast('CodeRubricAssessorProvider', assessor)

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

            code_assessor_client = httpx.Client()
            app.state.code_rubric_assessor_provider = JevCodeRubricAssessorProvider(
                api_key=settings.openrouter_api_key,
                client=code_assessor_client,
                decisions_url=str(settings.openrouter_decisions_url),
                model=settings.jev_model,
            )
            app.state.max_activity_payload_bytes = settings.max_activity_payload_bytes
            app.state.max_code_assessment_input_bytes = (
                settings.max_code_assessment_input_bytes
            )
            app.state.cache_provider = cache_provider
            broker = cast('InngestBroker', app.state.inngest_broker)
            broker.start()
            try:
                yield
            finally:
                broker.stop()
                await asyncio.to_thread(code_assessor_client.close)
                await cache_provider.close()
                database_engine.dispose()

        app = FastAPI(title='Shifu API', version='0.1.0', lifespan=lifespan)
        inngest_client = InngestMessaging.register(
            app,
            job_group_registrars=[
                lambda inngest: IdentityInngestMessaging.register_jobs(
                    inngest,
                    identity_database=identity_database,
                    clock_provider=clock_provider,
                ),
                lambda inngest: CommunicationInngestMessaging.register_jobs(
                    inngest,
                    communication_database=communication_database,
                    id_provider=id_provider,
                    clock_provider=clock_provider,
                    secret_envelope_provider=secret_envelope_provider,
                    message_renderer_provider=message_renderer_provider,
                    email_delivery_provider=email_delivery_provider,
                ),
                partial(
                    LearningInngestMessaging.register_jobs,
                    learning_database=learning_database,
                    clock_provider=clock_provider,
                    curriculum_content_provider=curriculum_content_provider,
                    code_rubric_assessor_provider_factory=code_rubric_assessor_provider_factory,
                    max_code_assessment_input_bytes=(
                        settings.max_code_assessment_input_bytes
                    ),
                ),
                partial(
                    GamificationInngestMessaging.register_jobs,
                    gamification_database=gamification_database,
                    curriculum_content_provider=curriculum_content_provider,
                    clock_provider=clock_provider,
                ),
            ],
        )
        app.state.inngest_broker = InngestBroker(
            inngest_client,
            engine=database_engine,
            id_provider=id_provider,
        )
        AppErrorHandler.register(app)
        app.state.identity_database = identity_database
        app.state.communication_database = communication_database
        app.state.confirmation_delivery_gateway = confirmation_workflow
        app.state.password_recovery_delivery_gateway = password_recovery_workflow
        app.state.communication_message_renderer_provider = message_renderer_provider
        app.state.communication_secret_envelope_provider = secret_envelope_provider
        app.state.email_delivery_provider = email_delivery_provider
        app.state.authentication_provider = authentication_provider
        app.state.identifier_provider = id_provider
        app.state.learning_database = learning_database
        app.state.gamification_database = gamification_database
        app.state.clock_provider = clock_provider
        app.state.curriculum_database = curriculum_database
        app.state.curriculum_content_provider = curriculum_content_provider
        app.state.curriculum_catalog_provider = curriculum_catalog_provider
        app.state.intelligence_database = SqlalchemyIntelligenceDatabase(
            engine=database_engine,
            id_provider=id_provider,
        )
        FastAPIApp._register_routers(app)
        app.add_middleware(
            RateLimitMiddleware,
            trusted_proxy_ips=settings.trusted_proxy_ips,
            bff_shared_secret=ENVIRONMENT.bff_shared_secret,
        )
        app.add_middleware(
            ActivityPayloadLimitMiddleware,
            max_body_bytes=settings.max_activity_payload_bytes,
        )
        return app


app = FastAPIApp.register()
