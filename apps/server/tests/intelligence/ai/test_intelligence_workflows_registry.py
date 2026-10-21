from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from time import monotonic, sleep
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from pydantic import PostgresDsn
from sqlalchemy import create_engine, text

from shifu.intelligence.ai import intelligence_workflows_registry as registry_module
from shifu.intelligence.ai.agno.workflows.agno_generate_mentor_title_workflow import (
    AgnoGenerateMentorTitleWorkflow,
)
from shifu.intelligence.ai.agno.workflows.purge_mentor_attachments_workflow import (
    PurgeMentorAttachmentsWorkflow,
)
from shifu.intelligence.ai.intelligence_workflows_registry import (
    IntelligenceWorkflowsRegistry,
)
from shifu.intelligence.core.domain.events.mentor_attachment_cleanup_requested_event import (
    MentorAttachmentCleanupRequestedEvent,
    MentorAttachmentCleanupRequestedPayload,
)
from shifu.intelligence.core.domain.events.mentor_attachment_preparation_requested_event import (
    MentorAttachmentPreparationRequestedEvent,
    MentorAttachmentPreparationRequestedPayload,
)
from shifu.intelligence.core.domain.events.mentor_response_requested_event import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorTitleOutputInvalidError,
    MentorTitleUnavailableError,
)
from shifu.intelligence.core.use_cases import PurgeLearnerMemoriesForAccountUseCase
from shifu.intelligence.providers.memory_classification.tfidf.tfidf_learner_memory_analyzer_provider import (
    TfidfLearnerMemoryAnalyzerProvider,
)
from shifu.intelligence.providers.mentor_title.agentos.agentos_mentor_title_provider import (
    AgentOSMentorTitleProvider,
)
from shifu.intelligence.providers.text_similarity.bag_of_words.bag_of_words_learner_memory_similarity_provider import (
    BagOfWordsLearnerMemorySimilarityProvider,
)
from shifu.intelligence.providers.routing.lazy_mentor_route_provider import (
    LazyMentorRouteProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces.outbox_event import OutboxEvent
from shifu.shared.messaging.agentos.agentos_client import (
    AgentOSClient,
    AgentOSClientError,
)
from shifu.shared.settings import Settings

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces import LearnerMemoryAnalyzerProvider
    from agno.models.base import Model
    from fastapi import FastAPI
    from sqlalchemy.engine import Engine
    from typing import Literal

    from shifu.intelligence.core.interfaces import MentorTelemetryProvider
    from shifu.intelligence.core.use_cases import (
        PurgeMentorAttachmentsUseCase,
    )
    from shifu.shared.core.domain.structures import MentorContextSnapshot
    from shifu.shared.core.interfaces import (
        MentorAccessProvider,
        MentorCatalogProvider,
        MentorContextProvider,
    )
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

    from shifu.shared.providers.langfuse_telemetry_provider import (
        LangfuseTelemetryProvider,
    )
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )
    from shifu.shared.providers.s3_file_storage_provider import S3FileStorageProvider


type _Projector = Callable[[OutboxEvent], tuple[str, Mapping[str, str]] | None]

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _NamedPytestNode(Protocol):
    name: str


@pytest.fixture(autouse=True)
def _agentos_submissions(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> list[str]:
    workflow_ids: list[str] = []
    original_submit = AgentOSClient.submit_workflow

    def capture_submission(
        client: AgentOSClient,
        *,
        workflow_id: str,
        fields: Mapping[str, str],
        background: bool,
        session_id: str,
        timeout_seconds: float = 610.0,
    ) -> dict[str, object]:
        workflow_ids.append(workflow_id)
        return original_submit(
            client,
            workflow_id=workflow_id,
            fields=fields,
            background=background,
            session_id=session_id,
            timeout_seconds=timeout_seconds,
        )

    monkeypatch.setattr(AgentOSClient, 'submit_workflow', capture_submission)

    node_name = cast('_NamedPytestNode', request.node).name
    missing_profiles: dict[
        str, tuple[Literal['primary', 'reviewer', 'vision'], int | None]
    ] = {
        'test_registered_vision_fallback_runs_through_agentos': ('vision', None),
        'test_registered_writer_fallback_fails_closed_through_agentos': (
            'primary',
            1,
        ),
        'test_registered_attachment_answer_fallback_fails_closed_through_agentos': (
            'primary',
            2,
        ),
        'test_registered_reviewer_fallback_fails_closed_through_agentos': (
            'reviewer',
            None,
        ),
    }
    profile_override = missing_profiles.get(node_name)
    if profile_override is not None:
        from shifu.app import FastAPIApp

        original_register = cast('Callable[..., FastAPI]', FastAPIApp.register)
        provider = registry_module.OpenrouterMentorAnswerModelProvider
        missing_profile, missing_call = profile_override

        def register_with_unavailable_profile(
            *args: object, **kwargs: object
        ) -> FastAPI:
            original_build = provider.build
            profile_calls = 0

            def build_without_profile(
                settings: Settings,
                *,
                profile: Literal['primary', 'fallback', 'reviewer', 'vision'] = (
                    'primary'
                ),
            ) -> Model | None:
                nonlocal profile_calls
                if profile == missing_profile:
                    profile_calls += 1
                    if missing_call is None or profile_calls == missing_call:
                        return None
                return original_build(settings, profile=profile)

            monkeypatch.setattr(provider, 'build', staticmethod(build_without_profile))
            return original_register(*args, **kwargs)

        monkeypatch.setattr(
            FastAPIApp,
            'register',
            staticmethod(register_with_unavailable_profile),
        )
    return workflow_ids


class _StorageProvider:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


class _TrackedHttpClient(httpx.Client):
    def __init__(self) -> None:
        super().__init__(
            transport=httpx.MockTransport(lambda _request: httpx.Response(500))
        )
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1
        super().close()


class _RuntimeDouble:
    def __init__(
        self,
        *,
        workflow_event_projector: _Projector,
        observability: LangfuseTelemetryProvider | None,
        **_configuration: object,
    ) -> None:
        self.client: AgentOSClient = cast('AgentOSClient', object())
        self.workflow_event_projector = workflow_event_projector
        self.observability = observability or cast(
            'LangfuseTelemetryProvider', object()
        )
        self.start_count = 0
        self.close_count = 0
        self.start_error: BaseException | None = None

    async def start(self) -> None:
        self.start_count += 1
        if self.start_error is not None:
            raise self.start_error

    async def close(self) -> None:
        self.close_count += 1


@dataclass
class _RegistryHarness:
    registry: IntelligenceWorkflowsRegistry
    engine: Engine
    storage: _StorageProvider
    client: _TrackedHttpClient
    runtime: _RuntimeDouble | None


class _TitleHandoffStub:
    def __init__(
        self, *, result: object = 'A title', error: Exception | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.created: list[tuple[str, object]] = []
        self.taken: list[tuple[str, str]] = []
        self.discarded: list[str] = []

    def create(self, *, capability: str, input_value: object) -> str:
        self.created.append((capability, input_value))
        return 'opaque-reference'

    def take_result(self, reference: str, *, capability: str) -> object:
        self.taken.append((reference, capability))
        if self.error is not None:
            raise self.error
        return self.result

    def discard(self, reference: str) -> None:
        self.discarded.append(reference)


class _TitleClientStub:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.submission: dict[str, object] | None = None

    def submit_workflow(self, **kwargs: object) -> dict[str, object]:
        self.submission = kwargs
        if self.error is not None:
            raise self.error
        return {}


@contextmanager
def _registry_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    agentos_enabled: bool = False,
    observability: LangfuseTelemetryProvider | None = None,
    learner_memory_analyzer: LearnerMemoryAnalyzerProvider | None = None,
) -> Generator[_RegistryHarness]:
    storage = _StorageProvider()
    client = _TrackedHttpClient()
    engine = create_engine('sqlite://')
    runtime_instances: list[_RuntimeDouble] = []

    class _FileStoragePipeDouble:
        @staticmethod
        def create_file_storage_provider(_settings: Settings) -> S3FileStorageProvider:
            return cast('S3FileStorageProvider', storage)

    class _RuntimeFactory(_RuntimeDouble):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(
                workflow_event_projector=cast(
                    '_Projector', kwargs['workflow_event_projector']
                ),
                observability=cast(
                    'LangfuseTelemetryProvider | None', kwargs.get('observability')
                ),
            )
            runtime_instances.append(self)

    monkeypatch.setattr(registry_module, 'FileStoragePipe', _FileStoragePipeDouble)
    monkeypatch.setattr(registry_module, 'AgentOSRuntime', _RuntimeFactory)
    monkeypatch.setattr(
        IntelligenceWorkflowsRegistry,
        '_build_code_rubric_client',
        staticmethod(lambda: client),
    )

    settings = Settings(
        redis_url='redis://127.0.0.1:6379',
        agentos_database_url=(
            PostgresDsn('postgresql://agentos:agentos@127.0.0.1/agentos')
            if agentos_enabled
            else None
        ),
    )
    registry = IntelligenceWorkflowsRegistry(
        settings,
        observability,
        cast('MentorAccessProvider', object()),
        cast('MentorContextProvider', object()),
        cast('MentorCatalogProvider', object()),
        outbox_engine=engine,
        telemetry=cast('MentorTelemetryProvider', object()),
        learner_memory_analyzer=learner_memory_analyzer,
    )
    harness = _RegistryHarness(
        registry=registry,
        engine=engine,
        storage=storage,
        client=client,
        runtime=runtime_instances[0] if runtime_instances else None,
    )
    try:
        yield harness
    finally:
        asyncio.run(registry.close())
        engine.dispose()


def _outbox_event(name: str, payload: Mapping[str, object]) -> OutboxEvent:
    return OutboxEvent(
        id='event-1',
        name=name,
        payload=payload,
        destination='unrouted',
        status='pending',
        attempts=0,
        available_at=_NOW,
        reserved_by=None,
        reservation_expires_at=None,
        last_error_code=None,
        created_at=_NOW,
        updated_at=_NOW,
        published_at=None,
    )


def _to_outbox(
    event: (
        MentorResponseRequestedEvent
        | MentorAttachmentPreparationRequestedEvent
        | MentorAttachmentCleanupRequestedEvent
    ),
) -> OutboxEvent:
    return _outbox_event(event.name, asdict(event.payload))


def test_registry_exposes_lazy_learner_memory_collaborators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_fit(*_args: object) -> None:
        raise AssertionError('the TF-IDF fit must wait for the first analysis')

    monkeypatch.setattr(TfidfLearnerMemoryAnalyzerProvider, '_fit', fail_fit)

    with _registry_harness(monkeypatch) as harness:
        registry = harness.registry

        assert isinstance(
            registry.learner_memory_analyzer, TfidfLearnerMemoryAnalyzerProvider
        )
        assert isinstance(
            registry.learner_memory_similarity,
            BagOfWordsLearnerMemorySimilarityProvider,
        )
        assert isinstance(
            registry.purge_learner_memories_use_case,
            PurgeLearnerMemoriesForAccountUseCase,
        )
        # The edit path extracts concepts with spaCy only and never fits the classifier.
        concepts = registry.learner_memory_analyzer.concepts(
            'Prefiro exemplos em Python.'
        )
        assert [concept.key for concept in concepts] == ['exemplo', 'python']
        assert registry.learner_memory_similarity.similarity(
            'Prefiro exemplos em Python.', 'Agora prefiro exemplos em JavaScript.'
        ) == pytest.approx(0.5)


def test_registry_accepts_a_learner_memory_analyzer_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = cast('LearnerMemoryAnalyzerProvider', object())

    with _registry_harness(monkeypatch, learner_memory_analyzer=analyzer) as harness:
        assert harness.registry.learner_memory_analyzer is analyzer


def test_registry_projects_registered_events_to_id_only_agentos_tickets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _registry_harness(monkeypatch, agentos_enabled=True) as harness:
        registry = harness.registry
        projector = cast('_RuntimeDouble', harness.runtime).workflow_event_projector
        response = MentorResponseRequestedEvent(
            payload=MentorResponseRequestedPayload(attempt_id='attempt-1')
        )
        preparation = MentorAttachmentPreparationRequestedEvent(
            payload=MentorAttachmentPreparationRequestedPayload(
                attachment_id='attachment-1', generation=3
            )
        )
        cleanup = MentorAttachmentCleanupRequestedEvent(
            payload=MentorAttachmentCleanupRequestedPayload(
                account_id='account-1',
                session_id=None,
                batch_id=None,
                deletion_generation=4,
            )
        )

        assert registry.destination_for_event(_to_outbox(response)) == (
            'agentos:intelligence'
        )
        assert registry.destination_for_event(_to_outbox(preparation)) == (
            'agentos:intelligence'
        )
        assert registry.destination_for_event(_to_outbox(cleanup)) == (
            'agentos:intelligence'
        )
        assert (
            registry.destination_for_event(_outbox_event('unrelated/event', {})) is None
        )

        assert projector(_outbox_event('unrelated/event', {})) is None
        assert projector(_to_outbox(response)) == (
            'intelligence-process-mentor-response',
            {'attempt_id': 'attempt-1', 'event_id': 'event-1'},
        )
        assert projector(_outbox_event(response.name, {'attempt_id': ''})) is None
        assert projector(_to_outbox(preparation)) == (
            'intelligence-prepare-mentor-attachment',
            {
                'attachment_id': 'attachment-1',
                'generation': '3',
                'event_id': 'event-1',
            },
        )
        assert (
            projector(
                _outbox_event(
                    preparation.name,
                    {'attachment_id': 'attachment-1', 'generation': True},
                )
            )
            is None
        )
        assert projector(_to_outbox(cleanup)) == (
            'intelligence-purge-mentor-attachments',
            {'account_id': 'account-1', 'deletion_generation': '4'},
        )

        cleanup_session = MentorAttachmentCleanupRequestedEvent(
            payload=MentorAttachmentCleanupRequestedPayload(
                account_id='account-1',
                session_id='session-1',
                batch_id=None,
                deletion_generation=4,
            )
        )
        cleanup_batch = MentorAttachmentCleanupRequestedEvent(
            payload=MentorAttachmentCleanupRequestedPayload(
                account_id='account-1',
                session_id=None,
                batch_id='batch-1',
                deletion_generation=4,
            )
        )
        cleanup_both = MentorAttachmentCleanupRequestedEvent(
            payload=MentorAttachmentCleanupRequestedPayload(
                account_id='account-1',
                session_id='session-1',
                batch_id='batch-1',
                deletion_generation=4,
            )
        )
        assert projector(_to_outbox(cleanup_session)) == (
            'intelligence-purge-mentor-attachments',
            {
                'account_id': 'account-1',
                'deletion_generation': '4',
                'session_id': 'session-1',
            },
        )
        assert projector(_to_outbox(cleanup_batch)) == (
            'intelligence-purge-mentor-attachments',
            {
                'account_id': 'account-1',
                'deletion_generation': '4',
                'batch_id': 'batch-1',
            },
        )
        assert projector(_to_outbox(cleanup_both)) is None
        assert (
            projector(
                _outbox_event(
                    cleanup.name,
                    {
                        'account_id': None,
                        'deletion_generation': 4,
                        'session_id': None,
                        'batch_id': None,
                    },
                )
            )
            is None
        )


def test_registry_lifespan_fails_closed_without_runtime_and_close_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _registry_harness(monkeypatch) as harness:
        assert harness.registry.observability is not None
        with pytest.raises(ServiceUnavailableError, match='AGENTOS_DATABASE_URL'):
            _ = harness.registry.client

        async def enter_lifespan() -> None:
            async with harness.registry.lifespan():
                pytest.fail('A registry without AgentOS must not start')

        with pytest.raises(ServiceUnavailableError, match='AGENTOS_DATABASE_URL'):
            asyncio.run(enter_lifespan())

        asyncio.run(harness.registry.close())
        assert harness.storage.close_count == 1
        assert harness.client.close_count == 1


def test_registry_runtime_starts_and_releases_owned_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observability = cast('LangfuseTelemetryProvider', object())
    with _registry_harness(
        monkeypatch,
        agentos_enabled=True,
        observability=observability,
    ) as harness:
        runtime = cast('_RuntimeDouble', harness.runtime)
        assert harness.registry.observability is runtime.observability
        assert harness.registry.client is runtime.client

        async def use_lifespan() -> None:
            async with harness.registry.lifespan():
                assert runtime.start_count == 1

        asyncio.run(use_lifespan())
        asyncio.run(harness.registry.close())

        assert runtime.close_count == 1
        assert harness.storage.close_count == 1
        assert harness.client.close_count == 1


def test_registry_closes_resources_if_agentos_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _registry_harness(monkeypatch, agentos_enabled=True) as harness:
        runtime = cast('_RuntimeDouble', harness.runtime)
        runtime.start_error = RuntimeError('runtime failed to start')

        async def enter_lifespan() -> None:
            async with harness.registry.lifespan():
                pytest.fail('Failed runtime startup must not enter the lifespan')

        with pytest.raises(RuntimeError, match='runtime failed to start'):
            asyncio.run(enter_lifespan())

        assert runtime.start_count == 1
        assert runtime.close_count == 1
        assert harness.storage.close_count == 1
        assert harness.client.close_count == 1


@pytest.mark.parametrize(
    ('result', 'take_error', 'submit_error', 'expected_error'),
    [
        ('Safe title', None, None, None),
        (object(), None, None, MentorTitleUnavailableError),
        ('invalid', None, None, MentorTitleOutputInvalidError),
        ('unavailable', None, None, MentorTitleUnavailableError),
        (None, KeyError('expired'), None, MentorTitleUnavailableError),
        (
            None,
            None,
            AgentOSClientError('private workflow response'),
            MentorTitleUnavailableError,
        ),
    ],
)
def test_agentos_title_provider_accepts_only_completed_string_results(
    result: object,
    take_error: Exception | None,
    submit_error: Exception | None,
    expected_error: type[Exception] | None,
) -> None:
    handoffs = _TitleHandoffStub(result=result, error=take_error)
    client = _TitleClientStub(error=submit_error)
    provider = AgentOSMentorTitleProvider(
        cast('AgentOSClient', client), cast('AgentOSHandoffStore', handoffs)
    )

    if expected_error is None:
        assert provider.generate('Learner first message') == 'Safe title'
    else:
        with pytest.raises(expected_error):
            provider.generate('Learner first message')

    assert handoffs.created == [('mentor-title-generation', 'Learner first message')]
    assert client.submission == {
        'workflow_id': 'intelligence-generate-mentor-title',
        'fields': {'handoff_ref': 'opaque-reference'},
        'background': False,
        'session_id': 'title-opaque-reference',
        'timeout_seconds': 3.0,
    }
    if submit_error is None:
        assert handoffs.taken == [('opaque-reference', 'mentor-title-generation')]
    if submit_error is not None:
        assert handoffs.discarded == ['opaque-reference']


def test_title_workflow_requires_a_single_opaque_reference_field() -> None:
    assert (
        AgnoGenerateMentorTitleWorkflow._reference(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            None
        )
        is None
    )
    assert (
        AgnoGenerateMentorTitleWorkflow._reference(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            'not-json'
        )
        is None
    )
    assert (
        AgnoGenerateMentorTitleWorkflow._reference(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            '[]'
        )
        is None
    )
    assert (
        AgnoGenerateMentorTitleWorkflow._reference(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            json.dumps({'handoff_ref': 'safe', 'attempt_id': 'private'})
        )
        is None
    )
    assert (
        AgnoGenerateMentorTitleWorkflow._reference(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            json.dumps({'handoff_ref': 'safe'})
        )
        == 'safe'
    )


def test_purge_workflow_normalizes_and_validates_targeted_cleanup_requests() -> None:
    workflow = PurgeMentorAttachmentsWorkflow(
        cast('PurgeMentorAttachmentsUseCase', object())
    )
    request = workflow._parse_input(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        json.dumps(
            {
                'account_id': 'A' * 26,
                'session_id': 'B' * 26,
                'deletion_generation': '4',
            }
        )
    )
    assert request.account_id == 'A' * 26
    assert request.session_id == 'B' * 26
    assert request.deletion_generation == 4

    with pytest.raises(MentorAttachmentInvalidError):
        workflow._parse_input(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            {
                'account_id': 'A' * 26,
                'session_id': None,
                'batch_id': None,
                'deletion_generation': 4,
            }
        )

    clone = workflow.deep_copy(update={'test_marker': 'copied'})
    assert vars(clone).get('test_marker') == 'copied'


def test_lazy_route_provider_fails_closed_when_catalog_version_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shifu.intelligence.ai.data import mentor_resources as resources_module

    class _Resources:
        version = 'catalog-v2'

        def bind_catalog_version(self, _projection: object) -> None:
            return

    class _Catalog:
        def read_projection(self) -> object:
            return object()

    monkeypatch.setattr(resources_module, 'MentorResources', _Resources)
    with _registry_harness(monkeypatch) as harness:
        provider = LazyMentorRouteProvider(
            harness.registry.database,
            cast('MentorCatalogProvider', _Catalog()),
        )
        object.__setattr__(provider, '_catalog_version', 'catalog-v1')
        with pytest.raises(ServiceUnavailableError, match='precisa ser atualizado'):
            provider.route('question', cast('MentorContextSnapshot', object()))


def test_registered_title_fallback_runs_through_agentos_client(
    agentos_fixture: RegisteredAgentOSFixture,
    _agentos_submissions: list[str],
) -> None:
    submission_key = str(uuid4())
    response = agentos_fixture.client.post(
        '/intelligence/mentor-sessions',
        json={
            'submission_key': submission_key,
            'first_message': '  registered   fallback title  ',
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()['session']['title'] == 'registered fallback title'
    assert 'intelligence-generate-mentor-title' in _agentos_submissions


def test_registered_title_workflow_returns_a_controlled_generated_title(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
    _agentos_submissions: list[str],
) -> None:
    def controlled_title_run(_agent: object, _first_message: str) -> SimpleNamespace:
        return SimpleNamespace(content={'title': 'Título controlado'})

    monkeypatch.setattr(
        vars(registry_module)['_UnavailableTitleAgent'],
        'run',
        cast('Callable[..., object]', controlled_title_run),
    )

    response = agentos_fixture.client.post(
        '/intelligence/mentor-sessions',
        json={
            'submission_key': str(uuid4()),
            'first_message': 'Estudar frações equivalentes',
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()['session']['title'] == 'Título controlado'
    assert 'intelligence-generate-mentor-title' in _agentos_submissions


def test_registered_title_workflow_falls_back_on_invalid_and_unavailable_results(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
    _agentos_submissions: list[str],
) -> None:
    controlled_results: list[object] = [
        SimpleNamespace(content='not-json'),
        RuntimeError('controlled title provider failure'),
    ]

    def controlled_title_run(_agent: object, _first_message: str) -> object:
        result = controlled_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        vars(registry_module)['_UnavailableTitleAgent'],
        'run',
        cast('Callable[..., object]', controlled_title_run),
    )

    responses = [
        agentos_fixture.client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': str(uuid4()),
                'first_message': '  título   inválido  ',
            },
        ),
        agentos_fixture.client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': str(uuid4()),
                'first_message': '  título   indisponível  ',
            },
        ),
    ]

    assert [response.status_code for response in responses] == [201, 201]
    assert [response.json()['session']['title'] for response in responses] == [
        'título inválido',
        'título indisponível',
    ]
    assert _agentos_submissions.count('intelligence-generate-mentor-title') == 2


def test_registered_vision_fallback_runs_through_agentos(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    _agentos_submissions: list[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    session_response = agentos_fixture.client.post(
        '/intelligence/mentor-sessions',
        json={
            'submission_key': str(uuid4()),
            'first_message': 'Inspect an image attachment.',
        },
    )
    assert session_response.status_code == 201, session_response.text
    session_id = session_response.json()['session']['id']

    batch_response = agentos_fixture.client.post(
        '/intelligence/mentor-attachment-batches',
        json={'session_id': session_id},
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()['batch_id']

    image = Image.new('RGB', (2, 2), color=(40, 90, 160))
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    image.close()
    upload_response = agentos_fixture.client.post(
        f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
        data={'upload_key': str(uuid4())},
        files={'file': ('diagram.png', buffer.getvalue(), 'image/png')},
    )
    assert upload_response.status_code == 201, upload_response.text
    assert upload_response.json()['attachment_id']

    deadline = monotonic() + 45
    while monotonic() < deadline and not any(
        'Step extract-and-interpret failed' in record.getMessage()
        and 'Mentor attachment vision is unavailable' in record.getMessage()
        for record in caplog.records
    ):
        sleep(0.75)

    assert any(
        'Step extract-and-interpret failed' in record.getMessage()
        and 'Mentor attachment vision is unavailable' in record.getMessage()
        for record in caplog.records
    ), 'Registered AgentOS did not invoke the unavailable vision profile'
    assert 'vision' not in agentos_fixture.model_transport.model_profiles
    assert 'intelligence-generate-mentor-title' in _agentos_submissions

    with postgres_database.engine.connect() as connection:
        registered_runs = connection.execute(
            text(
                'SELECT count(*) FROM '
                'agentos_intelligence.agentos_workflow_runs '
                'WHERE workflow_id = :workflow_id'
            ),
            {'workflow_id': 'intelligence-prepare-mentor-attachment'},
        ).scalar_one()
    assert registered_runs >= 1


def test_registered_attachment_answer_and_reviewer_run_through_agentos(
    agentos_fixture: RegisteredAgentOSFixture,
    _agentos_submissions: list[str],
) -> None:
    from tests.intelligence.server.agentos.mentor_attachment_test_support import (
        MODEL_ANSWER,
        create_goal,
        create_session,
        submit_message_with_attachment,
        upload_ready_text_attachment,
        wait_for_session_response,
    )

    session_id = create_session(agentos_fixture.client)
    initial_response = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_response['response'])
    assert initial_snapshot['status'] == 'completed'

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )
    attachment_response = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id,
    )
    attachment_snapshot = cast('dict[str, object]', attachment_response['response'])
    assert attachment_snapshot['status'] == 'completed'

    message_page = cast('dict[str, object]', attachment_response['messages'])
    messages = cast('list[object]', message_page['items'])
    message_contents: list[str] = []
    for value in messages:
        if not isinstance(value, dict):
            continue
        message = cast('dict[str, object]', value)
        content = message.get('content')
        if isinstance(content, str):
            message_contents.append(content)
    assert any(MODEL_ANSWER in content for content in message_contents)
    assert 'intelligence-process-mentor-response' in _agentos_submissions
    assert {'primary', 'reviewer'} <= set(
        agentos_fixture.model_transport.model_profiles
    )


def test_registered_attachment_answer_fallback_fails_closed_through_agentos(
    agentos_fixture: RegisteredAgentOSFixture,
    _agentos_submissions: list[str],
) -> None:
    from tests.intelligence.server.agentos.mentor_attachment_test_support import (
        create_goal,
        create_session,
        submit_message_with_attachment,
        upload_ready_text_attachment,
        wait_for_session_response,
    )

    session_id = create_session(agentos_fixture.client)
    initial_response = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_response['response'])
    assert initial_snapshot['status'] == 'completed'

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )
    response = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id,
    )

    snapshot = cast('dict[str, object]', response['response'])
    assert snapshot['status'] == 'failed'
    assert 'intelligence-process-mentor-response' in _agentos_submissions


def test_registered_reviewer_fallback_fails_closed_through_agentos(
    agentos_fixture: RegisteredAgentOSFixture,
    _agentos_submissions: list[str],
) -> None:
    from tests.intelligence.server.agentos.mentor_attachment_test_support import (
        create_goal,
        create_session,
        submit_message_with_attachment,
        upload_ready_text_attachment,
        wait_for_session_response,
    )

    session_id = create_session(agentos_fixture.client)
    initial_response = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_response['response'])
    assert initial_snapshot['status'] == 'completed'

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )
    response = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id,
    )

    snapshot = cast('dict[str, object]', response['response'])
    assert snapshot['status'] == 'failed'
    assert 'intelligence-process-mentor-response' in _agentos_submissions
    assert 'primary' in agentos_fixture.model_transport.model_profiles
    assert 'reviewer' not in agentos_fixture.model_transport.model_profiles
