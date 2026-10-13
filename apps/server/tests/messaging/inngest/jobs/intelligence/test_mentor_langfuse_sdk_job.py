"""Actual Langfuse OTLP export consumed by the registered native Mentor job."""

import asyncio
import gzip
import json
import os
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from fastapi import FastAPI
from langfuse import Langfuse
from pydantic import HttpUrl, SecretStr
from sqlalchemy import select
import pytest

from shifu.composition.mentor_telemetry import build_mentor_telemetry_client
from shifu.shared.settings import Settings
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from shifu.shared.providers.system_identifier_provider.system_identifier_provider import (
    SystemIdentifierProvider,
)
from tests.fixtures import (
    mentor_job_fixture as harness,
)
from tests.fixtures.mentor_job_fixture import (
    seed_request,
    publish_and_wait,
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


def create_langfuse_mentor_test_app() -> FastAPI:
    sdk = build_mentor_telemetry_client(
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue] - BaseSettings supports this runtime option; generated model signature omits it.
            redis_url='redis://127.0.0.1:6379/0',
            mentor_telemetry_enabled=True,
            langfuse_public_key=SecretStr('pk-disposable-mentor-sdk'),
            langfuse_secret_key=SecretStr('sk-disposable-mentor-sdk'),
            langfuse_base_url=HttpUrl(os.environ['SHIFU_MENTOR_TEST_OTLP_ENDPOINT']),
        )
    )
    if sdk is None:
        raise RuntimeError('Controlled Langfuse SDK composition unavailable.')

    def actual_sdk_client(endpoint: str) -> Langfuse:
        del endpoint
        return sdk

    # Only factory construction is adapted; the SDK and production adapter run unchanged.
    with patch.object(harness, '_ThrowingTelemetryClient', actual_sdk_client):
        app = harness.create_mentor_test_app()
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        try:
            async with original_lifespan(application):
                yield
        finally:
            await asyncio.to_thread(sdk.flush)
            await asyncio.to_thread(sdk.shutdown)

    app.router.lifespan_context = lifespan
    return app


@pytest.fixture(scope='session')
def langfuse_ingestion() -> Iterator[list[dict[str, object]]]:
    exports: list[dict[str, object]] = []
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            from google.protobuf.json_format import MessageToDict
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
                ExportTraceServiceRequest,
            )

            # BaseHTTPRequestHandler normalizes leading // in self.path; inspect
            # the actual HTTP request target to catch exporter URL concatenation.
            assert self.requestline.split()[1] == '/api/public/otel/v1/traces'
            assert self.path == '/api/public/otel/v1/traces'
            assert self.headers.get('x-langfuse-ingestion-version') == '4'
            body = self.rfile.read(int(self.headers['content-length']))
            if self.headers.get('content-encoding') == 'gzip':
                body = gzip.decompress(body)
            request = ExportTraceServiceRequest.FromString(body)
            decoded = cast('dict[str, object]', MessageToDict(request))
            with lock:
                exports.append(decoded)
            self.send_response(200)
            self.send_header('content-type', 'application/x-protobuf')
            self.send_header('content-length', '0')
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    variable = 'SHIFU_MENTOR_TEST_OTLP_ENDPOINT'
    previous = os.environ.get(variable)
    sdk_environment = {
        name: os.environ.get(name)
        for name in ('OTEL_BSP_SCHEDULE_DELAY', 'LANGFUSE_FLUSH_INTERVAL')
    }
    # Delay only native OTLP batching, not the SDK score-consumer queue timeout.
    os.environ['OTEL_BSP_SCHEDULE_DELAY'] = '3600000'
    os.environ.pop('LANGFUSE_FLUSH_INTERVAL', None)
    telemetry_previous = os.environ.get('MENTOR_TELEMETRY_ENABLED')
    os.environ['MENTOR_TELEMETRY_ENABLED'] = 'false'
    os.environ[variable] = f'http://127.0.0.1:{server.server_port}'
    try:
        yield exports
    finally:
        if previous is None:
            os.environ.pop(variable, None)
        else:
            os.environ[variable] = previous
        if telemetry_previous is None:
            os.environ.pop('MENTOR_TELEMETRY_ENABLED', None)
        else:
            os.environ['MENTOR_TELEMETRY_ENABLED'] = telemetry_previous
        for name, value in sdk_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope='session')
def inngest_app_target(
    controlled_mentor_endpoint: tuple[object, str],
    langfuse_ingestion: list[dict[str, object]],
) -> tuple[str, bool]:
    del controlled_mentor_endpoint, langfuse_ingestion
    return (
        'tests.messaging.inngest.jobs.intelligence.test_mentor_langfuse_sdk_job:create_langfuse_mentor_test_app',
        True,
    )


@pytest.mark.usefixtures('prepared_mentor_index')
def test_registered_native_job_exports_anonymous_operational_spans_with_actual_sdk(
    inngest_fixture: 'InngestFixture',
    controlled_mentor_endpoint: tuple[harness._ControlledInference, str],  # pyright: ignore[reportPrivateUsage] - Actual shared inference harness, not a provider double.
    langfuse_ingestion: list[dict[str, object]],
) -> None:
    state, _ = controlled_mentor_endpoint
    state.reset('telemetry_metadata_only')
    inngest_fixture.restart_application()
    langfuse_ingestion.clear()
    identifiers = SystemIdentifierProvider()
    account_ids = (identifiers.generate(), identifiers.generate())
    first_session_id, first_learner_id, first_attempt_id = seed_request(
        inngest_fixture,
        'O que é uma lista em Python?',
        account_id=account_ids[0],
    )
    publish_and_wait(inngest_fixture, first_attempt_id, 'completed')
    assert state.requests == []
    assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
    with inngest_fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, first_attempt_id)
        assert attempt is not None and attempt.status == 'completed'
        assert attempt.usage_calls == []
        reply = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == first_learner_id
            )
        )
        assert reply is not None and reply.content.strip()
        assert 'Ainda não encontrei' not in reply.content
    assert state.metadata_requests == []
    assert langfuse_ingestion == [], 'SDK exported before the configured shutdown flush'
    # Graceful worker shutdown executes the real SDK flush before process exit.
    inngest_fixture.restart_application()
    assert langfuse_ingestion, 'Actual SDK exported no OTLP spans during shutdown'
    spans: list[dict[str, object]] = []
    for export in langfuse_ingestion:
        for resource in cast('list[dict[str, object]]', export['resourceSpans']):
            for scope in cast('list[dict[str, object]]', resource['scopeSpans']):
                spans.extend(cast('list[dict[str, object]]', scope['spans']))
    # Real provider spans cover local retrieval/persistence only. No model,
    # review, content, or identity-linked observation is expected.
    expected_names = {
        'context',
        'route',
        'local',
        'classify',
        'retrieve',
        'persist',
        'publish',
    }
    assert expected_names <= {span['name'] for span in spans}
    assert not {span['name'] for span in spans} & {
        'generate',
        'review',
        'mentor-inference',
        'mentor-answer',
        'mentor-review',
    }
    for span in spans:
        attributes: dict[str, object] = {}
        for attribute in cast('list[dict[str, object]]', span['attributes']):
            value = cast('dict[str, object]', attribute['value'])
            assert len(value) == 1
            attributes[cast('str', attribute['key'])] = next(iter(value.values()))
        assert 'user.id' not in attributes
        assert 'session.id' not in attributes
        assert 'langfuse.observation.input' not in attributes
        assert 'langfuse.observation.output' not in attributes
        metadata = {
            key.removeprefix('langfuse.observation.metadata.')
            for key in attributes
            if key.startswith('langfuse.observation.metadata.')
        }
        assert metadata <= {
            'correlation_id',
            'profile',
            'duration_ms',
            'outcome',
            'blocks',
        }
    encoded = json.dumps(langfuse_ingestion, ensure_ascii=False)
    assert 'O que é uma lista em Python?' not in encoded
    assert all(account_id not in encoded for account_id in account_ids)
    assert first_session_id not in encoded
