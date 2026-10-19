import asyncio

import pytest
from sqlalchemy import create_engine

from agno.workflow.workflow import Workflow

from shifu.shared.messaging.agentos.agentos_runtime import AgentOSRuntime
from shifu.shared.messaging.agentos.agentos_settings import AgentOSQueueSettings


def test_runtime_configures_each_workflow_with_its_shared_database() -> None:
    workflows = (
        Workflow(id='test-first', name='test-first'),
        Workflow(id='test-second', name='test-second'),
    )
    outbox_engine = create_engine('sqlite+pysqlite:///:memory:')
    runtime = AgentOSRuntime(
        module='intelligence',
        agentos_id='test-agentos',
        schema='agentos_test',
        database_url='postgresql+psycopg://unused:unused@localhost/unused',
        redis_url='redis://localhost:6379/0',
        queue_settings=AgentOSQueueSettings(
            max_concurrency=1,
            max_queue_depth=1,
            timeout_seconds=30,
        ),
        workflows=workflows,
        workflow_event_projector=lambda _event: None,
        outbox_engine=outbox_engine,
    )

    try:
        database = workflows[0].db
        assert database is not None
        assert all(workflow.db is database for workflow in workflows)
        assert all(workflow.deep_copy().db is database for workflow in workflows)
    finally:
        asyncio.run(runtime.close())
        outbox_engine.dispose()


def test_runtime_rejects_empty_or_duplicate_workflow_ids() -> None:
    outbox_engine = create_engine('sqlite+pysqlite:///:memory:')

    def build_runtime(workflows: tuple[Workflow, ...]) -> AgentOSRuntime:
        return AgentOSRuntime(
            module='learning',
            agentos_id='test-agentos',
            schema='agentos_test',
            database_url='postgresql+psycopg://unused:unused@localhost/unused',
            redis_url='redis://localhost:6379/0',
            queue_settings=AgentOSQueueSettings(
                max_concurrency=1,
                max_queue_depth=1,
                timeout_seconds=30,
            ),
            workflows=workflows,
            workflow_event_projector=lambda _event: None,
            outbox_engine=outbox_engine,
        )

    try:
        with pytest.raises(ValueError, match='unique non-empty IDs'):
            build_runtime(())
        with pytest.raises(ValueError, match='unique non-empty IDs'):
            build_runtime(
                (
                    Workflow(id='duplicate', name='first'),
                    Workflow(id='duplicate', name='second'),
                )
            )
        with pytest.raises(ValueError, match='unique non-empty IDs'):
            build_runtime((Workflow(name='missing-id'),))
    finally:
        outbox_engine.dispose()


def test_closed_runtime_is_idempotent_and_cannot_restart() -> None:
    outbox_engine = create_engine('sqlite+pysqlite:///:memory:')
    runtime = AgentOSRuntime(
        module='learning',
        agentos_id='test-agentos',
        schema='agentos_test',
        database_url='postgresql+psycopg://unused:unused@localhost/unused',
        redis_url='redis://localhost:6379/0',
        queue_settings=AgentOSQueueSettings(
            max_concurrency=1,
            max_queue_depth=1,
            timeout_seconds=30,
        ),
        workflows=(Workflow(id='runtime-test', name='runtime-test'),),
        workflow_event_projector=lambda _event: None,
        outbox_engine=outbox_engine,
    )

    try:
        asyncio.run(runtime.close())
        asyncio.run(runtime.close())
        with pytest.raises(RuntimeError, match='already closed'):
            asyncio.run(runtime.start())
    finally:
        outbox_engine.dispose()
