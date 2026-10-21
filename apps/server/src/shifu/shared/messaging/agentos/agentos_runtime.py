"""Private module-local AgentOS runtime wiring shared by owning registries."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, suppress
from typing import TYPE_CHECKING, Literal

from agno.db.postgres import PostgresDb
from agno.job_queue.config import QueueConfig, RedisCoordination
from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from shifu.shared.messaging.agentos.agentos_broker import (
    AgentOSBroker,
    WorkflowEventProjector,
)
from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
from shifu.shared.providers.langfuse_telemetry_provider import (
    LangfuseTelemetryProvider,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agno.workflow.workflow import Workflow
    from sqlalchemy.engine import Engine
    from starlette.applications import Starlette

    from shifu.shared.messaging.agentos.agentos_settings import AgentOSQueueSettings


AgentOSModule = Literal['intelligence', 'learning']


class AgentOSRuntime:
    """Own one module's private app, queue store, client and outbox relay."""

    def __init__(
        self,
        *,
        module: AgentOSModule,
        agentos_id: str,
        schema: str,
        database_url: str,
        redis_url: str,
        queue_settings: AgentOSQueueSettings,
        workflows: Sequence[Workflow],
        workflow_event_projector: WorkflowEventProjector,
        outbox_engine: Engine,
        observability: LangfuseTelemetryProvider | None = None,
    ) -> None:
        if not database_url:
            raise ValueError('AGENTOS_DATABASE_URL is required')
        workflow_ids = frozenset(
            workflow.id for workflow in workflows if workflow.id is not None
        )
        if not workflow_ids or len(workflow_ids) != len(workflows):
            raise ValueError('AgentOS workflows need unique non-empty IDs')

        self._module = module
        self._database = PostgresDb(
            db_url=database_url,
            db_schema=schema,
            session_table='agentos_sessions',
            runs_table='agentos_workflow_runs',
            job_table='agentos_jobs',
            traces_table='agentos_traces',
            spans_table='agentos_spans',
            create_schema=False,
        )
        self._redis_client = Redis.from_url(  # pyright: ignore[reportUnknownMemberType] - redis-py defers option typing.
            redis_url
        )
        self._async_redis_client = AsyncRedis.from_url(  # pyright: ignore[reportUnknownMemberType] - redis-py defers option typing.
            redis_url
        )
        queue = QueueConfig(
            max_concurrency=queue_settings.max_concurrency,
            max_queue_depth=queue_settings.max_queue_depth,
            max_attempts=queue_settings.max_attempts,
            timeout_seconds=queue_settings.timeout_seconds,
            durable=True,
            db=self._database,
            redis=RedisCoordination(
                url=redis_url,
                sync_client=self._redis_client,
                async_client=self._async_redis_client,
                key_prefix=f'shifu:{module}:agentos',
            ),
        )
        for workflow in workflows:
            if workflow.db is None:
                workflow.db = self._database
        self._agentos = AgentOS(
            id=agentos_id,
            workflows=list(workflows),
            db=self._database,
            settings=AgnoAPISettings(
                env='production',
                docs_enabled=False,
                authorization_enabled=False,
            ),
            tracing=False,
            telemetry=False,
            auto_provision_dbs=False,
            queue=queue,
        )
        self.internal_app: Starlette = self._agentos.get_app()
        self.client = AgentOSClient(
            self.internal_app,
            service_token=self._service_token(),
            workflow_ids=workflow_ids,
        )
        self.broker = AgentOSBroker(
            module=module,
            client=self.client,
            workflow_event_projector=workflow_event_projector,
            engine=outbox_engine,
        )
        self.observability = observability or LangfuseTelemetryProvider(module)
        self._native_lifespan: AbstractAsyncContextManager[object] | None = None
        self._native_started = False
        self._closed = False

    async def start(self) -> None:
        if self._closed:
            raise RuntimeError('AgentOS runtime is already closed')
        if self._native_lifespan is not None:
            return
        native_lifespan = self.internal_app.router.lifespan_context(self.internal_app)
        self._native_lifespan = native_lifespan
        try:
            await native_lifespan.__aenter__()
            self._native_started = True
            await self.client.start()
            self.broker.start()
        except BaseException:
            with suppress(Exception):
                await self.close()
            raise

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.broker.stop()
        with suppress(Exception):
            await self.client.close()
        lifespan = self._native_lifespan
        self._native_lifespan = None
        if lifespan is not None and self._native_started:
            with suppress(Exception):
                await lifespan.__aexit__(None, None, None)
        self._native_started = False
        with suppress(Exception):
            await self._async_redis_client.aclose()
        with suppress(Exception):
            self._redis_client.close()
        with suppress(Exception):
            self._database.db_engine.dispose()

    @staticmethod
    def _service_token() -> str:
        import secrets

        return secrets.token_urlsafe(48)
