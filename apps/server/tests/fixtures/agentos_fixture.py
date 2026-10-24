"""Registered AgentOS integration fixtures with disposable local dependencies."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, cast
from unittest.mock import create_autospec

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from shifu.app import FastAPIApp
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    MentorAccessGrant,
)
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.pipes import AuthenticationPipe, FileStoragePipe, SharedPipe
from shifu.shared.providers.s3_file_storage_provider import (
    S3FileStorageProvider,
    S3FileStorageSettings,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.settings import get_settings
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from threading import Event

    from fastapi import FastAPI
    from httpx2 import Request

    from shifu.intelligence.ai.agno.models.mentor_openai_chat import MentorOpenAIChat
    from shifu.shared.settings import Settings
    from tests.fixtures.postgres_fixture import PostgresDatabase
    from tests.fixtures.redis_fixture import RedisFixture


class InMemoryFileStorageProvider(S3FileStorageProvider):
    """Request-scoped attachment storage that never contacts an object store."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, object_key: str, content: bytes, media_type: str) -> None:
        self.objects[object_key] = (content, media_type)

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    def remove(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    def close(self) -> None:
        self.objects.clear()


class ControlledMentorModelTransport:
    """Capture actual model requests and return schema-valid local responses."""

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []
        self.openai_clients: list[OpenAI] = []
        self.model_profiles: list[str] = []
        self.reject_attachment_source = False
        self.reported_cost_usd: float | None = None
        # Planner scenarios: queued outputs are consumed in order, then defaults apply.
        self.planner_interview_outputs: list[dict[str, object]] = []
        self.planner_proposal_outputs: list[dict[str, object]] = []
        self.planner_failing_models: set[str] = set()
        self.planner_gate: Event | None = None
        self.planner_block_first = 0
        self.planner_requests: list[dict[str, object]] = []
        self.planner_models: list[str] = []

    def build_client(self) -> OpenAI:
        client = OpenAI(
            api_key='local-agentos-test-key',
            base_url='https://openrouter.ai/api/v1',
            http_client=httpx2.Client(
                transport=httpx2.MockTransport(self._handle_request)
            ),
        )
        self.openai_clients.append(client)
        return client

    def close(self) -> None:
        for client in self.openai_clients:
            client.close()

    def _handle_request(self, request: Request) -> httpx2.Response:
        payload = cast('dict[str, object]', json.loads(request.content))
        self.requests.append(payload)
        schema = self._response_schema(payload)
        properties_value = schema.get('properties', {})
        properties = (
            cast('dict[str, object]', properties_value)
            if isinstance(properties_value, dict)
            else {}
        )
        keys = set(properties)
        output: dict[str, object]

        if {'answer', 'sources'} <= keys:
            input_payload = self._find_payload(payload, 'allowed_sources')
            sources = input_payload.get('allowed_sources')
            source_list = (
                cast('list[object]', sources) if isinstance(sources, list) else []
            )
            selected_source = (
                cast('dict[str, object]', source_list[0])
                if source_list and isinstance(source_list[0], dict)
                else None
            )
            if selected_source is not None and self.reject_attachment_source:
                selected_source = {
                    **selected_source,
                    'chunk_id': 'Z' * 26,
                }
            output = {
                'answer': 'O trecho anexado explica o conceito solicitado.',
                'sources': [selected_source] if selected_source is not None else [],
            }
        elif {
            'request_adherence',
            'fact_fidelity',
            'cumulative_solution',
            'diagnostic_safety',
            'privacy_access',
            'official_action_claims',
        } <= keys:
            approved = {'choice': 'approved', 'feedback': ''}
            output = {
                key: dict(approved)
                for key in (
                    'request_adherence',
                    'fact_fidelity',
                    'cumulative_solution',
                    'diagnostic_safety',
                    'privacy_access',
                    'official_action_claims',
                )
            }
        elif {'needs_clarification', 'questions'} <= keys:
            return self._planner_response(payload, self._planner_interview_output())
        elif {'supported', 'title', 'description', 'skills'} <= keys:
            return self._planner_response(
                payload, self._planner_proposal_output(payload)
            )
        elif {'description', 'legible'} <= keys:
            output = {'description': 'Texto visual analisado.', 'legible': True}
        elif {'block_key', 'ordinal', 'content'} <= keys:
            input_payload = self._find_payload(payload, 'block_key')
            output = {
                'block_key': input_payload.get('block_key', 'generated-answer'),
                'ordinal': input_payload.get('ordinal', 0),
                'intent': input_payload.get('intent'),
                'content': 'Explicação educacional local.',
                'sources': [],
            }
        else:
            return httpx2.Response(500, json={'error': 'Unsupported local schema'})

        return httpx2.Response(
            200,
            json={
                'id': 'chatcmpl-agentos-fixture',
                'object': 'chat.completion',
                'created': 1,
                'model': payload.get('model', 'local-fixture'),
                'choices': [
                    {
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': json.dumps(output, ensure_ascii=False),
                        },
                        'finish_reason': 'stop',
                    }
                ],
                'usage': {
                    'prompt_tokens': 17,
                    'completion_tokens': 13,
                    'total_tokens': 30,
                    **(
                        {'cost': self.reported_cost_usd}
                        if self.reported_cost_usd is not None
                        else {}
                    ),
                },
            },
        )

    def _planner_response(
        self, payload: dict[str, object], output: dict[str, object]
    ) -> httpx2.Response:
        self.planner_requests.append(self._find_payload(payload, 'intent'))
        model = str(payload.get('model'))
        self.planner_models.append(model)
        if self.planner_block_first > 0 and self.planner_gate is not None:
            self.planner_block_first -= 1
            # Long enough for a slow runner to observe the operation timeout first.
            self.planner_gate.wait(timeout=90)
        if model in self.planner_failing_models:
            return httpx2.Response(500, json={'error': 'Planner model unavailable'})
        return httpx2.Response(
            200,
            json={
                'id': 'chatcmpl-agentos-planner',
                'object': 'chat.completion',
                'created': 1,
                'model': payload.get('model', 'local-fixture'),
                'choices': [
                    {
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': json.dumps(output, ensure_ascii=False),
                        },
                        'finish_reason': 'stop',
                    }
                ],
                'usage': {
                    'prompt_tokens': 21,
                    'completion_tokens': 11,
                    'total_tokens': 32,
                },
            },
        )

    def _planner_interview_output(self) -> dict[str, object]:
        if self.planner_interview_outputs:
            return self.planner_interview_outputs.pop(0)
        return {'needs_clarification': False, 'questions': []}

    def _planner_proposal_output(self, payload: dict[str, object]) -> dict[str, object]:
        if self.planner_proposal_outputs:
            return self.planner_proposal_outputs.pop(0)
        candidates = self._find_payload(payload, 'candidates').get('candidates')
        entries = (
            cast('list[dict[str, object]]', candidates)
            if isinstance(candidates, list)
            else []
        )
        preferred = [
            entry
            for entry in entries
            if entry.get('name') in {'React', 'JavaScript essencial', 'HTML e CSS'}
        ] or entries[:1]
        return {
            'supported': True,
            'title': 'Aprender desenvolvimento web',
            'description': 'Um caminho do HTML ao React para construir sites interativos.',
            'skills': [
                {
                    'skill_id': entry['skill_id'],
                    'justification': f'Base para {entry["name"]}.',
                }
                for entry in preferred
            ],
        }

    @staticmethod
    def _response_schema(payload: dict[str, object]) -> dict[str, object]:
        response_format = payload.get('response_format')
        if not isinstance(response_format, dict):
            return {}
        response_format = cast('dict[str, object]', response_format)
        json_schema = response_format.get('json_schema')
        if not isinstance(json_schema, dict):
            return {}
        schema = cast('dict[str, object]', json_schema).get('schema')
        return cast('dict[str, object]', schema) if isinstance(schema, dict) else {}

    @staticmethod
    def _find_payload(
        payload: dict[str, object], required_key: str
    ) -> dict[str, object]:
        messages = payload.get('messages')
        if isinstance(messages, list):
            for message in cast('list[object]', messages):
                if not isinstance(message, dict):
                    continue
                message = cast('dict[str, object]', message)
                content = message.get('content')
                content_items = (
                    cast('list[object]', content)
                    if isinstance(content, list)
                    else [content]
                )
                for item in content_items:
                    if isinstance(item, dict):
                        text = cast('dict[str, object]', item).get('text')
                    else:
                        text = item
                    if not isinstance(text, str):
                        continue
                    try:
                        parsed: object = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict) and required_key in parsed:
                        return cast('dict[str, object]', parsed)
        return {}


class ControlledDecisionsTransport:
    """Answer the planner's Jev classification; other decisions keep their client.

    Suites that exercise code assessment patch the registry's rubric client factory
    with their own transport before the registered app is built; this transport only
    intercepts `planning_intent` requests and forwards everything else to the client
    that factory produces, so both kinds of decisions stay controlled.
    """

    def __init__(
        self, fallback_factory: Callable[[], httpx.Client] | None = None
    ) -> None:
        self.kind = 'learning'
        self.fail_next = 0
        self.requests: list[dict[str, object]] = []
        self._fallback_factory = fallback_factory
        self._fallback_client: httpx.Client | None = None

    def build_client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self._handle))

    def close(self) -> None:
        if self._fallback_client is not None:
            self._fallback_client.close()
            self._fallback_client = None

    def _handle(self, request: httpx.Request) -> httpx.Response:
        payload = cast('dict[str, object]', json.loads(request.content))
        questions = payload.get('questions')
        if not isinstance(questions, dict) or 'planning_intent' not in questions:
            return self._forward(request)
        self.requests.append(payload)
        if self.fail_next > 0:
            self.fail_next -= 1
            return httpx.Response(503, json={'error': 'busy'})
        kinds = ('learning', 'out-of-scope', 'ambiguous')
        return httpx.Response(
            200,
            json={
                'answers': {
                    'planning_intent': {
                        'type': 'choice',
                        'choice': self.kind,
                        'confidence': 0.9,
                        'probabilities': {
                            kind: 0.9 if kind == self.kind else 0.05 for kind in kinds
                        },
                    }
                }
            },
        )

    def _forward(self, request: httpx.Request) -> httpx.Response:
        if self._fallback_factory is None:
            return httpx.Response(503, json={'error': 'decisions unavailable'})
        if self._fallback_client is None:
            self._fallback_client = self._fallback_factory()
        forwarded = self._fallback_client.build_request(
            request.method,
            str(request.url),
            headers=request.headers,
            content=request.content,
        )
        return self._fallback_client.send(forwarded)


@dataclass(frozen=True, slots=True)
class RegisteredAgentOSFixture:
    client: TestClient
    model_transport: ControlledMentorModelTransport
    account: AuthenticatedUser
    storage: InMemoryFileStorageProvider
    decisions: ControlledDecisionsTransport = field(
        default_factory=ControlledDecisionsTransport
    )


@pytest.fixture
def agentos_telemetry_environment() -> dict[str, str]:
    """Keep ordinary runtime tests isolated from developer monitoring credentials."""
    return {
        'MENTOR_TELEMETRY_ENABLED': 'false',
        'LANGFUSE_PUBLIC_KEY': '',
        'LANGFUSE_SECRET_KEY': '',
        'LANGFUSE_BASE_URL': 'http://127.0.0.1:1',
    }


def _reset_agno_process_globals() -> None:
    """Make the next AgentOS instance wire its own Redis managers.

    Agno installs one cancellation manager and one event stream per process the
    first time a queue with Redis coordination starts, then keeps them for every
    later instance. Their async Redis client belongs to the event loop of the
    test that created them, so a later test in the same process would run with
    a closed loop (`Cancellation check unavailable ... Event loop is closed`).
    """
    from agno.os import event_streams as agno_event_streams
    from agno.run import cancel as agno_cancel
    from agno.run.cancellation_management.in_memory_cancellation_manager import (
        InMemoryRunCancellationManager,
    )

    agno_cancel._cancellation_manager = InMemoryRunCancellationManager()  # noqa: SLF001 - the fixture resets Agno's process-wide defaults on purpose. # pyright: ignore[reportPrivateUsage]
    agno_cancel._cancellation_manager_explicitly_set = False  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]
    agno_event_streams._event_stream = None  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]
    agno_event_streams._event_stream_explicitly_set = False  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]


@pytest.fixture
def agentos_fixture(
    monkeypatch: pytest.MonkeyPatch,
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
    agentos_telemetry_environment: dict[str, str],
) -> Iterator[RegisteredAgentOSFixture]:
    """Start the owning FastAPI app and both native AgentOS registries."""

    if os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1':
        pytest.skip('Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests')

    monkeypatch.setenv('AGENTOS_DATABASE_URL', postgres_database.agentos_url)
    monkeypatch.setenv('REDIS_URL', redis_fixture.url)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'local-agentos-test-key')
    monkeypatch.setenv('OPENROUTER_PROMPT_LOGGING_DISABLED', 'true')
    monkeypatch.setenv('MENTOR_TITLE_PROMPT_LOGGING_DISABLED', 'false')
    monkeypatch.setenv('PLANNING_OPERATION_TIMEOUT_SECONDS', '10')
    for name, value in agentos_telemetry_environment.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    _reset_agno_process_globals()

    from shifu.intelligence.providers.openrouter import (
        MentorTitleModelProvider,
    )
    from shifu.intelligence.providers.openrouter.mentor_answer_model_provider import (
        OpenrouterMentorAnswerModelProvider,
    )
    from shifu.intelligence.ai.intelligence_workflows_registry import (
        IntelligenceWorkflowsRegistry,
    )
    from shifu.intelligence.providers.openrouter.planner_model_provider import (
        OpenrouterPlannerModelProvider,
    )
    from shifu.curriculum.database.sqlalchemy.curriculum_database import (
        SqlalchemyCurriculumDatabase,
    )
    from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
        CurriculumMentorCatalogProvider,
    )
    from shifu.intelligence.ai.data.mentor_resources import MentorResources
    from shifu.intelligence.database.mentor_embeddings_database_repository import (
        MentorEmbeddingsDatabaseRepository,
    )
    from shifu.intelligence.pipes.intelligence_pipe import IntelligencePipe
    from shifu.intelligence.prepare_mentor_indexes import prepare_indexes
    from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
        SentenceTransformersEmbeddingsProvider,
    )

    catalog = CurriculumMentorCatalogProvider(
        SqlalchemyCurriculumDatabase(engine=postgres_database.engine)
    )
    version = prepare_indexes(
        SentenceTransformersEmbeddingsProvider(),
        MentorEmbeddingsDatabaseRepository(
            IntelligencePipe.create_database(postgres_database.engine)
        ),
        catalog,
        MentorResources(),
    )
    assert version

    model_transport = ControlledMentorModelTransport()
    original_build = OpenrouterMentorAnswerModelProvider.build

    def controlled_model(
        settings: Settings,
        *,
        profile: Literal['primary', 'fallback', 'reviewer', 'vision'] = 'primary',
    ) -> MentorOpenAIChat | None:
        model = original_build(settings, profile=profile)
        if model is None:
            raise AssertionError(
                f'Registered AgentOS model profile is unavailable: {profile}'
            )
        model_transport.model_profiles.append(profile)
        model.client = model_transport.build_client()
        return model

    monkeypatch.setattr(
        'shifu.intelligence.ai.intelligence_workflows_registry.OpenrouterMentorAnswerModelProvider.build',
        controlled_model,
    )

    original_planner_build = OpenrouterPlannerModelProvider.build

    def controlled_planner_model(
        settings: Settings,
        *,
        profile: Literal['primary', 'fallback'] = 'primary',
    ) -> MentorOpenAIChat | None:
        model = original_planner_build(settings, profile=profile)
        if model is None:
            raise AssertionError(
                f'Registered AgentOS planner model profile is unavailable: {profile}'
            )
        model_transport.model_profiles.append(f'planner-{profile}')
        model.client = model_transport.build_client()
        return model

    monkeypatch.setattr(
        'shifu.intelligence.ai.intelligence_workflows_registry.OpenrouterPlannerModelProvider.build',
        controlled_planner_model,
    )
    rubric_client_factory = IntelligenceWorkflowsRegistry._build_code_rubric_client  # noqa: SLF001 - the fixture seams the private factory on purpose. # pyright: ignore[reportPrivateUsage]
    decisions = ControlledDecisionsTransport(rubric_client_factory)
    monkeypatch.setattr(
        IntelligenceWorkflowsRegistry,
        '_build_code_rubric_client',
        staticmethod(decisions.build_client),
    )

    def no_title_model(_settings: Settings) -> None:
        return None

    monkeypatch.setattr(MentorTitleModelProvider, 'build', no_title_model)

    storage = InMemoryFileStorageProvider()

    def in_memory_storage(_settings: S3FileStorageSettings) -> S3FileStorageProvider:
        return storage

    monkeypatch.setattr(
        FileStoragePipe, 'create_file_storage_provider', in_memory_storage
    )

    account = AuthenticatedUser(
        account_id=SystemIdentifierProvider().generate(),
        display_name='AgentOS Fixture Learner',
        time_zone=None,
    )
    access = create_autospec(MentorAccessProvider, instance=True)

    def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
        return MentorAccessGrant(
            account_id=account_id,
            access_revision='agentos-test-revision',
            operation_key=operation_key,
        )

    access.authorize.side_effect = grant
    app: FastAPI = FastAPIApp.register(
        postgres_database.engine,
        mentor_access_provider=access,
    )
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: account
    app.dependency_overrides[AuthenticationPipe.get_authenticated_user] = lambda: (
        account
    )
    headers = {
        'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret,
        'Authorization': 'Bearer agentos-fixture-token',
    }

    try:
        with TestClient(app, headers=headers) as client:
            yield RegisteredAgentOSFixture(
                client, model_transport, account, storage, decisions
            )
    finally:
        model_transport.close()
        get_settings.cache_clear()
        _reset_agno_process_globals()
