from asyncio import to_thread
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial
from typing import ClassVar, cast

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
from shifu.composition.agent_monitoring import (
    build_agent_monitoring_client,
    close_agent_monitoring_client,
)
from shifu.curriculum.database.sqlalchemy import (
    SqlalchemyCurriculumDatabase,
)
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
    CurriculumMentorCatalogProvider,
)
from shifu.curriculum.rest.router import CurriculumRouter
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.messaging.inngest import GamificationInngestMessaging
from shifu.gamification.rest.router import GamificationRouter
from shifu.identity.core.domain.events import AccountDeletedEvent
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.messaging.inngest import IdentityInngestMessaging
from shifu.identity.providers.auth.jwt.jwks.jwks_jwt_authentication_provider import (
    JwksJwtAuthenticationProvider,
)
from shifu.identity.providers.identity_mentor_access_provider import (
    IdentityMentorAccessProvider,
)
from shifu.identity.rest.router import IdentityRouter
from shifu.intelligence.ai.intelligence_workflows_registry import (
    IntelligenceWorkflowsRegistry,
)
from shifu.intelligence.core.interfaces import (
    MentorRouteProvider,
    MentorTelemetryProvider,
)
from shifu.intelligence.rest.router import IntelligenceRouter
from shifu.intelligence.rest.mentor_attachment_body_limit_middleware import (
    MentorAttachmentBodyLimitMiddleware,
)
from shifu.intelligence.rest.intelligence_error_handler import (
    IntelligenceErrorHandler,
)
from shifu.intelligence.rest.mentor_attachment_error_handler import (
    MentorAttachmentErrorHandler,
)
from shifu.learning.rest.learning_error_handler import LearningErrorHandler
from shifu.intelligence.messaging.inngest.intelligence_inngest_messaging import (
    IntelligenceInngestMessaging,
)
from shifu.learning.ai.learning_workflows_registry import (
    LearningWorkflowsRegistry,
)
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.messaging.inngest import LearningInngestMessaging
from shifu.learning.core.domain.events import MentorSkillActionResolvedEvent
from shifu.learning.providers.learning_mentor_context_provider import (
    LearningMentorContextProvider,
)
from shifu.learning.providers.learning_mentor_goal_destinations_provider import (
    LearningMentorGoalDestinationsProvider,
)
from shifu.learning.rest.router import LearningRouter
from shifu.rest.handlers import AppErrorHandler
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import (
    MentorAccessProvider,
    MentorContextProvider,
    MentorGoalDestinationsProvider,
)
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.messaging.inngest import InngestBroker, InngestMessaging
from shifu.shared.providers.cache.redis.redis_cache_provider import (
    RedisCacheProvider,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
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


class PrivateMentorNoStoreMiddleware:
    _PRIVATE_PATH_PREFIXES: ClassVar[tuple[str, ...]] = (
        '/intelligence/mentor-sessions',
        '/intelligence/learner-memories',
    )

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get('path', ''))
        if scope['type'] != 'http' or not path.startswith(self._PRIVATE_PATH_PREFIXES):
            await self._app(scope, receive, send)
            return

        async def send_private(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = [
                    (name, value)
                    for name, value in message.get('headers', [])
                    if name.lower() != b'cache-control'
                ]
                headers.append((b'cache-control', b'private, no-store'))
                message['headers'] = headers
            await send(message)

        await self._app(scope, receive, send_private)


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
    def register(
        database_engine: Engine | None = None,
        *,
        mentor_access_provider: MentorAccessProvider | None = None,
        mentor_context_provider: MentorContextProvider | None = None,
        mentor_goal_destinations_provider: MentorGoalDestinationsProvider | None = None,
        mentor_route_provider: MentorRouteProvider | None = None,
        mentor_telemetry_provider: MentorTelemetryProvider | None = None,
    ) -> FastAPI:
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
        mentor_catalog_provider = CurriculumMentorCatalogProvider(curriculum_database)
        mentor_access_provider = mentor_access_provider or IdentityMentorAccessProvider(
            identity_database
        )
        mentor_context_provider = (
            mentor_context_provider
            or LearningMentorContextProvider(
                learning_database,
                mentor_catalog_provider,
                GetCompetencyDetailUseCase(
                    learning_database, curriculum_content_provider
                ),
            )
        )
        mentor_goal_destinations_provider = (
            mentor_goal_destinations_provider
            or LearningMentorGoalDestinationsProvider(learning_database)
        )
        intelligence_registry = IntelligenceWorkflowsRegistry(
            settings,
            None,
            mentor_access_provider,
            mentor_context_provider,
            mentor_catalog_provider,
            mentor_goal_destinations_provider,
            outbox_engine=database_engine,
            route_provider=mentor_route_provider,
            telemetry=mentor_telemetry_provider,
            curriculum_catalog_provider=curriculum_catalog_provider,
        )
        learning_registry = LearningWorkflowsRegistry(
            settings,
            None,
            intelligence_registry.code_rubric_assessor_provider,
            mentor_access_provider,
            curriculum_content_provider,
            outbox_engine=database_engine,
        )
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
                await intelligence_registry.close()
                await learning_registry.close()
                database_engine.dispose()
                raise ServiceUnavailableError(
                    message='O Redis está indisponível; o servidor não pode iniciar.'
                ) from error

            monitoring = build_agent_monitoring_client(settings)
            monitoring_client = monitoring.client if monitoring is not None else None
            app.state.agent_monitoring_client = monitoring_client
            app.state.agent_monitoring_tracer_provider = (
                monitoring.tracer_provider if monitoring is not None else None
            )
            intelligence_registry.observability_provider.bind(monitoring_client)
            learning_registry.observability_provider.bind(monitoring_client)
            app.state.max_activity_payload_bytes = settings.max_activity_payload_bytes
            app.state.max_code_assessment_input_bytes = (
                settings.max_code_assessment_input_bytes
            )
            app.state.cache_provider = cache_provider
            broker = cast('InngestBroker', app.state.inngest_broker)
            try:
                async with AsyncExitStack() as stack:
                    await stack.enter_async_context(intelligence_registry.lifespan())
                    await stack.enter_async_context(learning_registry.lifespan())
                    app.state.code_rubric_assessor_provider = (
                        learning_registry.code_rubric_assessor_provider
                    )
                    broker.start()
                    try:
                        yield
                    finally:
                        broker.stop()
            finally:
                intelligence_registry.observability_provider.bind(None)
                learning_registry.observability_provider.bind(None)
                try:
                    await to_thread(close_agent_monitoring_client, monitoring)
                finally:
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
                lambda inngest: IntelligenceInngestMessaging.register_jobs(
                    inngest,
                    purge_mentor_attachments_use_case=(
                        intelligence_registry.purge_mentor_attachments_use_case
                    ),
                    purge_mentor_summaries_use_case=(
                        intelligence_registry.purge_mentor_summaries_use_case
                    ),
                    purge_learner_memories_use_case=(
                        intelligence_registry.purge_learner_memories_use_case
                    ),
                    purge_mentor_action_proposals_use_case=(
                        intelligence_registry.purge_mentor_action_proposals_use_case
                    ),
                    record_mentor_action_outcome_use_case=(
                        intelligence_registry.record_mentor_action_outcome_use_case
                    ),
                    account_deleted_event_name=AccountDeletedEvent.EVENT_NAME,
                    mentor_action_resolved_event_name=(
                        MentorSkillActionResolvedEvent.EVENT_NAME
                    ),
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
            destination_resolver=lambda event: (
                intelligence_registry.destination_for_event(event)
                or learning_registry.destination_for_event(event)
                or 'inngest'
            ),
            id_provider=id_provider,
        )
        AppErrorHandler.register(app)
        MentorAttachmentErrorHandler.register(app)
        IntelligenceErrorHandler.register(app)
        LearningErrorHandler.register(app)
        app.state.identity_database = identity_database
        app.state.communication_database = communication_database
        app.state.confirmation_delivery_gateway = confirmation_workflow
        app.state.password_recovery_delivery_gateway = password_recovery_workflow
        app.state.communication_message_renderer_provider = message_renderer_provider
        app.state.communication_secret_envelope_provider = secret_envelope_provider
        app.state.email_delivery_provider = email_delivery_provider
        app.state.authentication_provider = authentication_provider
        app.state.identifier_provider = id_provider
        app.state.learning_database = learning_registry.database
        app.state.gamification_database = gamification_database
        app.state.clock_provider = clock_provider
        app.state.curriculum_database = curriculum_database
        app.state.curriculum_content_provider = curriculum_content_provider
        app.state.curriculum_catalog_provider = curriculum_catalog_provider
        app.state.intelligence_database = intelligence_registry.database
        app.state.mentor_access_provider = mentor_access_provider
        app.state.mentor_context_provider = mentor_context_provider
        app.state.mentor_goal_destinations_provider = mentor_goal_destinations_provider
        app.state.mentor_route_provider = intelligence_registry.route_provider
        app.state.mentor_catalog_provider = mentor_catalog_provider
        app.state.planning_intent_classifier_provider = (
            intelligence_registry.planning_intent_classifier
        )
        app.state.planning_skill_retrieval_provider = (
            intelligence_registry.planning_skill_retrieval
        )
        app.state.intelligence_workflows_registry = intelligence_registry
        app.state.learning_workflows_registry = learning_registry
        app.state.generate_mentor_title_provider = (
            intelligence_registry.mentor_title_provider
        )
        app.state.learner_memory_analyzer_provider = (
            intelligence_registry.learner_memory_analyzer_provider
        )
        app.state.file_storage_provider = intelligence_registry.file_storage_provider
        app.state.mentor_attachment_extractor_provider = (
            intelligence_registry.attachment_extractor_provider
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
        app.add_middleware(PrivateMentorNoStoreMiddleware)
        app.add_middleware(MentorAttachmentBodyLimitMiddleware)
        return app


app = FastAPIApp.register()
