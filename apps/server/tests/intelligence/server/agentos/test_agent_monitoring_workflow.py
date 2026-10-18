"""Actual Langfuse OTLP export through registered module AgentOS boundaries."""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.intelligence.database.sqlalchemy.models import MentorMessageModel
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
)
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    ATTACHMENT_TEXT,
    MODEL_ANSWER,
    create_goal,
    create_session,
    submit_message_with_attachment,
    upload_ready_text_attachment,
    wait_for_session_response,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI
    from langfuse import Langfuse
    from opentelemetry.sdk.trace import TracerProvider

    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)


@dataclass
class _Ingestion:
    endpoint: str = ''
    status: int = 200
    mode: str = ''
    exports: list[dict[str, object]] = field(default_factory=list)
    targets: list[tuple[str, str | None]] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)
    shutdown_expected: bool = False
    no_requests_expected: bool = False
    lifecycle: list[str] = field(default_factory=list)

    def spans(self) -> list[dict[str, object]]:
        spans: list[dict[str, object]] = []
        with self.lock:
            exports = list(self.exports)
        for export in exports:
            for resource in cast('list[dict[str, object]]', export['resourceSpans']):
                for scope in cast('list[dict[str, object]]', resource['scopeSpans']):
                    spans.extend(cast('list[dict[str, object]]', scope['spans']))
        return spans


@pytest.fixture
def monitoring_ingestion() -> Iterator[_Ingestion]:
    ingestion = _Ingestion()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            from google.protobuf.json_format import MessageToDict
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
                ExportTraceServiceRequest,
            )

            body = self.rfile.read(int(self.headers['content-length']))
            if self.headers.get('content-encoding') == 'gzip':
                body = gzip.decompress(body)
            decoded = cast(
                'dict[str, object]',
                MessageToDict(ExportTraceServiceRequest.FromString(body)),
            )
            with ingestion.lock:
                ingestion.targets.append(
                    (
                        self.requestline.split()[1],
                        self.headers.get('x-langfuse-ingestion-version'),
                    )
                )
                ingestion.exports.append(decoded)
            self.send_response(ingestion.status)
            self.send_header('content-type', 'application/x-protobuf')
            self.send_header('content-length', '0')
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    ingestion.endpoint = f'http://127.0.0.1:{server.server_port}'
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield ingestion
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if ingestion.shutdown_expected:
            assert len(ingestion.lifecycle) == 4
            assert set(ingestion.lifecycle[:2]) == {'intelligence', 'learning'}
            assert ingestion.lifecycle[2] == 'monitoring_shutdown'
            assert ingestion.lifecycle[3] == 'otel_shutdown'
            assert ingestion.exports
        elif ingestion.no_requests_expected:
            assert ingestion.targets == []


@pytest.fixture
def agentos_telemetry_environment(
    request: pytest.FixtureRequest,
    monitoring_ingestion: _Ingestion,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    mode = cast('str', request.param)
    monitoring_ingestion.mode = mode
    monitoring_ingestion.no_requests_expected = mode in {'disabled', 'missing_keys'}
    monitoring_ingestion.status = 400 if mode == 'exporter_failure' else 200
    monkeypatch.setenv('OTEL_BSP_SCHEDULE_DELAY', '3600000')
    return {
        'MENTOR_TELEMETRY_ENABLED': 'false' if mode == 'disabled' else 'true',
        'MENTOR_TELEMETRY_CONTENT_ENABLED': 'true',
        'LANGFUSE_PUBLIC_KEY': f'pk-disposable-agent-monitoring-{uuid4().hex}',
        'LANGFUSE_SECRET_KEY': ''
        if mode == 'missing_keys'
        else 'sk-disposable-agent-monitoring',
        'LANGFUSE_BASE_URL': monitoring_ingestion.endpoint,
    }


@pytest.fixture(autouse=True)
def controlled_learning_model(
    monkeypatch: pytest.MonkeyPatch,
    monitoring_ingestion: _Ingestion,
) -> Iterator[list[dict[str, object]]]:
    requests: list[dict[str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(cast('dict[str, object]', json.loads(request.content)))
        if monitoring_ingestion.mode == 'provider_failure':
            raise RuntimeError('private-monitoring-provider-exception-marker')
        return httpx.Response(
            200,
            json={
                'answers': {
                    'rubric:correctness': {'type': 'choice', 'choice': 'level-100'}
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(
        'shifu.intelligence.ai.intelligence_workflows_registry.IntelligenceWorkflowsRegistry._build_code_rubric_client',
        staticmethod(lambda: client),
    )
    try:
        yield requests
    finally:
        client.close()


def _attributes(span: dict[str, object]) -> dict[str, object]:
    attributes: dict[str, object] = {}
    for attribute in cast('list[dict[str, object]]', span.get('attributes', [])):
        value = cast('dict[str, object]', attribute['value'])
        attributes[cast('str', attribute['key'])] = next(iter(value.values()))
    return attributes


def _observe_shutdown(
    application: FastAPI, ingestion: _Ingestion, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdk = cast('Langfuse | None', application.state.agent_monitoring_client)
    if sdk is not None:
        ingestion.shutdown_expected = True
        intelligence = application.state.intelligence_workflows_registry
        learning = application.state.learning_workflows_registry
        intelligence_close = intelligence.close
        learning_close = learning.close
        sdk_shutdown = sdk.shutdown
        tracer = cast(
            'TracerProvider', application.state.agent_monitoring_tracer_provider
        )
        tracer_shutdown = tracer.shutdown

        async def close_intelligence() -> None:
            await intelligence_close()
            ingestion.lifecycle.append('intelligence')

        async def close_learning() -> None:
            await learning_close()
            ingestion.lifecycle.append('learning')

        def shutdown_monitoring() -> None:
            sdk_shutdown()
            ingestion.lifecycle.append('monitoring_shutdown')
            if ingestion.mode == 'shutdown_failure':
                raise RuntimeError('controlled monitoring shutdown failure')

        def shutdown_otel() -> None:
            tracer_shutdown()
            ingestion.lifecycle.append('otel_shutdown')

        # Observe public lifecycle boundaries while preserving their real work.
        # The collector outlives agentos_fixture and asserts this order at teardown.
        monkeypatch.setattr(intelligence, 'close', close_intelligence)
        monkeypatch.setattr(learning, 'close', close_learning)
        monkeypatch.setattr(sdk, 'shutdown', shutdown_monitoring)
        monkeypatch.setattr(tracer, 'shutdown', shutdown_otel)


class TestAgentMonitoringWorkflow:
    @pytest.mark.parametrize(
        'agentos_telemetry_environment',
        [
            'enabled',
            'exporter_failure',
            'disabled',
            'missing_keys',
            'provider_failure',
            'shutdown_failure',
        ],
        indirect=True,
    )
    def test_registered_attachment_response_exports_safe_usage_or_remains_available(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monitoring_ingestion: _Ingestion,
        agentos_telemetry_environment: dict[str, str],
        controlled_learning_model: list[dict[str, object]],
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        application = cast('FastAPI', agentos_fixture.client.app)
        learning = application.state.learning_workflows_registry
        _observe_shutdown(application, monitoring_ingestion, monkeypatch)
        private_values = [
            ATTACHMENT_TEXT,
            MODEL_ANSWER,
            agentos_fixture.account.account_id,
            'Quero conversar sobre como estudar usando o documento anexado.',
            'local-agentos-test-key',
            'private-monitoring-learning-prompt',
            'private-monitoring-learning-code',
            'private-monitoring-provider-exception-marker',
        ]
        if monitoring_ingestion.mode == 'enabled':
            agentos_fixture.model_transport.reported_cost_usd = 0.0125
            session_id = create_session(agentos_fixture.client)
            wait_for_session_response(agentos_fixture.client, session_id)
            batch_id, attachment_id = upload_ready_text_attachment(
                agentos_fixture.client, session_id=session_id
            )
            goal_id = create_goal(agentos_fixture.client)
            attempt_id = submit_message_with_attachment(
                agentos_fixture.client,
                session_id=session_id,
                batch_id=batch_id,
                attachment_id=attachment_id,
                goal_id=goal_id,
            )
            detail = wait_for_session_response(
                agentos_fixture.client, session_id, attempt_id=attempt_id
            )
            response = cast('dict[str, object]', detail['response'])
            assert response['status'] == 'completed', detail
            learner_message_id = cast('str', response['learner_message_id'])
            with Session(postgres_database.engine) as session:
                answer = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_message_id
                    )
                )
                assert answer is not None and MODEL_ANSWER in answer.content
            assert agentos_fixture.model_transport.requests

            private_values.extend(
                (session_id, learner_message_id, attempt_id, attachment_id)
            )
        assessment = CodeRubricAssessmentInput(
            question_kind='javascript_stdin',
            prompt='private-monitoring-learning-prompt',
            project_files=(('src/main.js', 'private-monitoring-learning-code'),),
            submitted_paths=('src/main.js',),
            rubric_criteria=(
                CurriculumCodeRubricCriterionSnapshot(
                    key='correctness',
                    name='Correctness',
                    description='Print the required greeting.',
                    weight_percentage=100,
                    required=True,
                    fixed_comments=tuple(
                        CurriculumCodeRubricCommentSnapshot(
                            id=f'level-{level}', level=level, text=f'Level {level}'
                        )
                        for level in (0, 25, 50, 75, 100)
                    ),
                    inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
                        id='unknown', text='Unable to assess.'
                    ),
                ),
            ),
            concept_criteria=(),
        )
        if monitoring_ingestion.mode == 'provider_failure':
            with pytest.raises(ServiceUnavailableError):
                learning.code_rubric_assessor.assess(assessment)
        else:
            decisions = learning.code_rubric_assessor.assess(assessment)
            assert len(decisions.criterion_levels) == 1
            assert decisions.criterion_levels[0].key == 'correctness'
            assert decisions.criterion_levels[0].level == 100
            assert decisions.concept_levels == ()
        assert len(controlled_learning_model) == 1
        assert 'private-monitoring-learning-code' in json.dumps(
            controlled_learning_model
        )
        sdk = cast('Langfuse | None', application.state.agent_monitoring_client)
        if (
            agentos_telemetry_environment['MENTOR_TELEMETRY_ENABLED'] == 'false'
            or not agentos_telemetry_environment['LANGFUSE_SECRET_KEY']
        ):
            assert sdk is None
            assert monitoring_ingestion.exports == []
            assert monitoring_ingestion.targets == []
            return

        assert sdk is not None
        sdk.flush()
        spans = monitoring_ingestion.spans()
        assert spans, 'Actual SDK exported no registered AgentOS observations'
        assert 'learning.evaluate' in {span['name'] for span in spans}
        assert set(monitoring_ingestion.targets) == {
            ('/api/public/otel/v1/traces', '4')
        }
        attributes = [_attributes(span) for span in spans]
        if monitoring_ingestion.mode == 'enabled':
            generations = [
                item
                for item in attributes
                if item.get('langfuse.observation.type') == 'generation'
            ]
            assert generations, 'Model execution exported no generation observations'
            usage = [
                json.loads(cast('str', item['langfuse.observation.usage_details']))
                for item in generations
            ]
            assert {'input': 17, 'output': 13, 'total': 30} in usage
            costs = [
                json.loads(cast('str', item['langfuse.observation.cost_details']))
                for item in generations
                if 'langfuse.observation.cost_details' in item
            ]
            assert {'total': 0.0125} in costs
            generation_trace_ids = {
                span['traceId']
                for span in spans
                if _attributes(span).get('langfuse.observation.type') == 'generation'
            }
            assert any(
                span['traceId'] in generation_trace_ids
                and span['name'] == 'intelligence.review'
                for span in spans
            ), 'Inference and review observations lost their shared correlation'
        for item in attributes:
            assert 'user.id' not in item
            assert 'session.id' not in item
            assert 'langfuse.observation.input' not in item
            assert 'langfuse.observation.output' not in item
            if item.get('langfuse.observation.metadata.module') == 'learning':
                assert 'langfuse.observation.usage_details' not in item
                assert 'langfuse.observation.cost_details' not in item
                assert 'langfuse.observation.metadata.tokens' not in item
                assert 'langfuse.observation.metadata.cost_usd' not in item
            metadata = {
                key.removeprefix('langfuse.observation.metadata.')
                for key in item
                if key.startswith('langfuse.observation.metadata.')
            }
            assert metadata <= {
                'module',
                'stage',
                'outcome',
                'duration_ms',
                'model_profile',
                'tokens',
                'input_tokens',
                'output_tokens',
                'cost_usd',
                'blocks',
                'observations',
                'matches',
                'inference_requests',
                'criteria',
            }
        if monitoring_ingestion.mode == 'provider_failure':
            assert any(
                item.get('langfuse.observation.metadata.outcome') == 'failed'
                and item.get('langfuse.observation.level') == 'ERROR'
                for item in attributes
            )
        encoded = json.dumps(monitoring_ingestion.exports, ensure_ascii=False)
        for private_value in private_values:
            assert private_value not in encoded
            assert private_value not in caplog.text
