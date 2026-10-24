"""The Mentor response workflow run in process over the disposable PostgreSQL and
Redis, with the three agents replaced by mocks. Use cases, repositories and the
generation limit are real; the route, context and catalog providers are mocks."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import uuid4

from agno.metrics import RunMetrics
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from fastapi.testclient import TestClient
import pytest

from shifu.curriculum.core.domain.enums import ActivityType
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
    CurriculumMentorCatalogProvider,
)
from shifu.fakers.curriculum.entities import ActivityFaker, CompetencyFaker, SkillFaker
from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.intelligence.ai.agno.agents import (
    MentorAttachmentAnswerAgent,
    MentorReviewerAgent,
    MentorWriterAgent,
)
from shifu.intelligence.ai.agno.outputs import (
    MentorAnswerBlockOutput,
    MentorAttachmentAnswerOutput,
    MentorAttachmentSourceOutput,
)
from shifu.intelligence.ai.agno.workflows import AgnoProcessMentorResponseWorkflow
from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources
from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.ai.data.mentor_inference_usage import report_inference_usage
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryAnalysis,
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
    MentorEmbeddingMatch,
    MentorResponseBlock,
    MentorReviewResult,
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces import (
    LearnerMemoryAnalyzerProvider,
    LearnerMemorySimilarityProvider,
    MentorConversationSummarizerProvider,
    MentorEmbeddingsProvider,
    MentorEmbeddingsRepository,
    MentorGenerationLimitProvider,
    MentorRouteProvider,
    MentorTelemetryProvider,
)
from shifu.intelligence.core.use_cases import (
    AssertMentorResponseCurrentUseCase,
    FailMentorResponseUseCase,
    FinalizeMentorResponseUseCase,
    GetMentorAttachmentContextUseCase,
    PrepareMentorResponseUseCase,
    PublishMentorResponseBlockUseCase,
    RecordMentorInferenceUsageUseCase,
    RecordMentorResponseProgressUseCase,
    ReleaseMentorResponseClaimUseCase,
    RemoveMentorSessionUseCase,
    RenewMentorResponseClaimUseCase,
    SummarizeMentorSessionContextUseCase,
    UpdateLearnerMemoriesUseCase,
)
from shifu.intelligence.providers.generation_limit.redis.redis_mentor_generation_limit_provider import (
    RedisMentorGenerationLimitProvider,
)
from shifu.intelligence.providers.generation_limit.unavailable_mentor_generation_limit_provider import (
    UnavailableMentorGenerationLimitProvider,
)
from shifu.intelligence.providers.routing.local.local_mentor_route_provider import (
    LocalMentorRouteProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.providers.learning_mentor_context_provider import (
    LearningMentorContextProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    MentorAccessGrant,
    MentorContextSnapshot,
)
from shifu.shared.core.interfaces import (
    MentorAccessProvider,
    MentorCatalogProvider,
    MentorContextProvider,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.pipes import FileStoragePipe
from tests.fixtures.intelligence_fixture import (
    MENTOR_ACCOUNT,
    OTHER_ACCOUNT,
    IntelligenceFixture,
    MentorAttachmentExtractorStub,
    MentorAttachmentStorageStub,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from shifu.curriculum.core.domain.entities import Skill
    from shifu.learning.core.domain.entities import Goal, SkillExperience

    from shifu.intelligence.core.domain.structures import (
        MentorGenerationRequest,
        MentorResponseSnapshot,
    )
    from tests.fixtures.redis_fixture import RedisFixture

ABSTENTION_TEXT = 'Essas informações estão indisponíveis no momento.'
FIRST_ANSWER = 'Olá! Posso ajudar com conceitos, dicas e organização dos estudos.'
SECOND_ANSWER = 'Olá! Me diga qual Habilidade você está estudando para eu ajudar.'
LOCAL_ANSWER = 'Uma fração equivalente mantém a mesma proporção: 1/2 = 2/4.'
ATTACHMENT_ANSWER = 'O arquivo diz que um meio é igual a dois quartos: 1/2 = 2/4.'
ATTACHMENT_QUESTION = 'O que o arquivo anexado diz sobre frações?'
CHUNK_TEXT = 'Um meio pode ser escrito como dois quartos: 1/2 = 2/4.'
ABSTENTION_KEY = PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY
CRITERIA = (
    'request_adherence',
    'fact_fidelity',
    'cumulative_solution',
    'diagnostic_safety',
    'privacy_access',
    'official_action_claims',
)


def written(content: str, *, tokens: int = 15) -> RunOutput:
    """A completed writer run, as the mocked writer agent returns it."""
    return RunOutput(
        content=MentorAnswerBlockOutput(
            block_key='generated-0', ordinal=0, intent=None, content=content
        ),
        status=RunStatus.completed,
        metrics=RunMetrics(
            input_tokens=tokens - 5, output_tokens=5, total_tokens=tokens
        ),
    )


def review(*, approved: bool) -> MentorReviewResult:
    """One review result; the real reviewer also reports its usage, so the
    scripted reviewer below does the same before returning it."""
    return MentorReviewResult(
        approved=approved,
        criteria=tuple(
            (
                name,
                'approved' if approved or name != 'fact_fidelity' else 'rejected',
                None,
            )
            for name in CRITERIA
        ),
        correction=None if approved else 'Revise a resposta: fact_fidelity',
    )


class ScriptedReviewer:
    """The mocked reviewer: one verdict per call, the last one repeated."""

    def __init__(
        self, verdicts: tuple[bool, ...], *, before: Callable[[], None] | None = None
    ) -> None:
        self._verdicts = list(verdicts)
        self._before = before

    def __call__(self, *_args: object) -> MentorReviewResult:
        if self._before is not None:
            self._before()
        approved = (
            self._verdicts.pop(0) if len(self._verdicts) > 1 else self._verdicts[0]
        )
        report_inference_usage('review:0', 'mentor-reviewer', 12)
        return review(approved=approved)


def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
    return MentorAccessGrant(
        account_id=account_id,
        access_revision='controlled-test-revision',
        operation_key=operation_key,
    )


def empty_context(*_args: object, **_kwargs: object) -> MentorContextSnapshot:
    return MentorContextSnapshot(
        goal_id=None,
        skill_experience_id=None,
        skill_id=None,
        competency_id=None,
        activity_id=None,
        skill_completed=None,
        diagnostic_in_progress=False,
        facts=(),
        eligible_references=(),
        resolved_references=(),
        unavailable_sources=(),
    )


def unanswered_route(
    content: str, _context: MentorContextSnapshot, _topics: tuple[str, ...] = ()
) -> MentorRouteResult:
    """The local router found no answer: the abstention plus one unanswered part."""
    return MentorRouteResult(
        intents=(),
        local_blocks=(
            MentorResponseBlock(
                block_key=ABSTENTION_KEY,
                ordinal=0,
                intent=None,
                content=ABSTENTION_TEXT,
            ),
        ),
        generation_requests=(content,),
        clarification=None,
        unanswered_requests=(content,),
    )


def local_route(
    _content: str, _context: MentorContextSnapshot, _topics: tuple[str, ...] = ()
) -> MentorRouteResult:
    """The local router answered everything: no generation request at all."""
    return MentorRouteResult(
        intents=(),
        local_blocks=(
            MentorResponseBlock(
                block_key='faq-fractions', ordinal=0, intent=None, content=LOCAL_ANSWER
            ),
        ),
        generation_requests=(),
        clarification=None,
    )


def progress_context(*facts: tuple[str, str]) -> MentorContextSnapshot:
    """A learner context carrying the given Learning facts and nothing else."""
    base = empty_context()
    return MentorContextSnapshot(
        goal_id=base.goal_id,
        skill_experience_id=base.skill_experience_id,
        skill_id=base.skill_id,
        competency_id=base.competency_id,
        activity_id=base.activity_id,
        skill_completed=base.skill_completed,
        diagnostic_in_progress=base.diagnostic_in_progress,
        facts=facts,
        eligible_references=base.eligible_references,
        resolved_references=base.resolved_references,
        unavailable_sources=base.unavailable_sources,
    )


def real_route(
    similarities: dict[str, float], context: MentorContextSnapshot | None = None
) -> Callable[..., MentorRouteResult]:
    """The real local route over a stubbed index that scores each intent as given.

    Embedding vectors are placeholders: only the per-intent similarities the index
    returns decide which intents the classifier keeps. Without a fixed context, the
    route reads the one the use case passes.
    """

    def embed(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.0,) for _ in texts)

    def nearest(corpus: str, *_args: object) -> tuple[MentorEmbeddingMatch, ...]:
        if corpus != 'intents':
            return ()
        return tuple(
            MentorEmbeddingMatch(
                reference_id=intent, variation_key='0', similarity=similarity
            )
            for intent, similarity in similarities.items()
        )

    embeddings = Mock(spec=MentorEmbeddingsProvider)
    embeddings.embed_queries.side_effect = embed
    repository = Mock(spec=MentorEmbeddingsRepository)
    repository.find_nearest.side_effect = nearest
    telemetry = Mock(spec=MentorTelemetryProvider)
    telemetry.scope.return_value = nullcontext()
    provider = LocalMentorRouteProvider(
        embeddings,
        repository,
        SpacyMentorTextPreprocessorProvider(),
        MentorResources(),
        telemetry,
    )

    def route(
        content: str, passed: MentorContextSnapshot, topics: tuple[str, ...] = ()
    ) -> MentorRouteResult:
        return provider.route(content, context or passed, topics)

    return route


def attachment_route(
    content: str, _context: MentorContextSnapshot, _topics: tuple[str, ...] = ()
) -> MentorRouteResult:
    """An attachment-backed question: nothing local, one request for the file."""
    return MentorRouteResult(
        intents=(),
        local_blocks=(),
        generation_requests=(content,),
        clarification=None,
    )


def attachment_answer(
    attachment_id: str, chunk_id: str
) -> Callable[..., MentorAttachmentAnswerOutput]:
    """The mocked attachment answerer: it reports its usage like the real one."""

    def answer(*_args: object, **_kwargs: object) -> MentorAttachmentAnswerOutput:
        report_inference_usage('attachment-answer:0', 'mentor-attachment-answer', 30)
        return MentorAttachmentAnswerOutput(
            answer=ATTACHMENT_ANSWER,
            sources=[
                MentorAttachmentSourceOutput(
                    attachment_id=attachment_id,
                    chunk_id=chunk_id,
                    page_number=None,
                    locator='chars:1-55#1',
                )
            ],
        )

    return answer


@dataclass
class Harness:
    fixture: IntelligenceFixture
    workflow: AgnoProcessMentorResponseWorkflow
    writer: Mock
    reviewer: Mock
    attachment_answer: Mock
    route: Mock
    limit: MentorGenerationLimitProvider
    context: Mock
    catalog: Mock

    def submit(self, account: AuthenticatedUser = MENTOR_ACCOUNT) -> tuple[str, str]:
        """Create a session over HTTP: one queued attempt for its first message."""
        with TestClient(
            self.fixture.mentor_app(account),
            headers={'Authorization': 'Bearer test-token'},
        ) as client:
            session_id, attempt_id, _ = self.fixture.create_session(client)
        return session_id, attempt_id

    def submit_message(
        self,
        content: str,
        context_hint: dict[str, str] | None = None,
        account: AuthenticatedUser = MENTOR_ACCOUNT,
    ) -> tuple[str, str]:
        """Open a conversation with the given first message and page hint."""
        with TestClient(
            self.fixture.mentor_app(account),
            headers={'Authorization': 'Bearer test-token'},
        ) as client:
            response = client.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': str(uuid4()),
                    'first_message': content,
                    'context_hint': context_hint,
                },
            )
        assert response.status_code == 201, response.text
        body = response.json()
        return str(body['session']['id']), str(body['response']['attempt_id'])

    def submit_follow_up(
        self,
        session_id: str,
        content: str,
        account: AuthenticatedUser = MENTOR_ACCOUNT,
    ) -> str:
        """Add a message to an open conversation; returns its attempt id."""
        with TestClient(
            self.fixture.mentor_app(account),
            headers={'Authorization': 'Bearer test-token'},
        ) as client:
            response = client.post(
                f'/intelligence/mentor-sessions/{session_id}/messages',
                json={'submission_key': str(uuid4()), 'content': content},
            )
        assert response.status_code == 202, response.text
        return str(response.json()['response']['attempt_id'])

    def answer(self, session_id: str, attempt_id: str) -> str:
        """Run an attempt to completion and return the published answer text."""
        self.run(attempt_id)
        assert self.status(attempt_id) is MentorResponseStatus.COMPLETED
        blocks = self.snapshot(session_id).blocks
        return '\n\n'.join(block.content for block in blocks)

    def ask(
        self, content: str, context_hint: dict[str, str] | None = None
    ) -> tuple[str, str]:
        """``(session_id, answer)`` of a message that opens a conversation."""
        session_id, attempt_id = self.submit_message(content, context_hint)
        return session_id, self.answer(session_id, attempt_id)

    def use_learning_data(self) -> None:
        """Read the Learning and Curriculum rows through the real context provider."""
        engine = self.fixture.postgres.engine
        curriculum = SqlalchemyCurriculumDatabase(engine)
        learning = SqlalchemyLearningDatabase(engine)
        catalog = CurriculumMentorCatalogProvider(curriculum)
        provider = LearningMentorContextProvider(
            learning,
            catalog,
            GetCompetencyDetailUseCase(
                learning, DatabaseCurriculumContentProvider(curriculum)
            ),
        )
        self.context.read.side_effect = provider.read
        self.catalog.read_projection.side_effect = catalog.read_projection
        self.catalog.search.side_effect = catalog.search

    def assert_no_model_call(self) -> None:
        self.writer.run.assert_not_called()
        self.reviewer.review.assert_not_called()
        self.attachment_answer.run.assert_not_called()

    def run(self, attempt_id: str) -> None:
        # The registered runtime runs the workflow asynchronously; so does the test.
        asyncio.run(self.workflow.arun(input=json.dumps({'attempt_id': attempt_id})))

    def snapshot(
        self, session_id: str, account: AuthenticatedUser = MENTOR_ACCOUNT
    ) -> MentorResponseSnapshot:
        with self.fixture.database.transaction() as repositories:
            snapshot = repositories.mentor_response_events.snapshot(
                account.account_id, session_id
            )
        assert snapshot is not None
        return snapshot

    def status(self, attempt_id: str) -> MentorResponseStatus:
        with self.fixture.database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id(attempt_id)
        assert attempt is not None
        return attempt.status

    def usage_keys(self, attempt_id: str) -> set[str]:
        with self.fixture.database.transaction() as repositories:
            usage = repositories.mentor_response_attempts.read_usage(attempt_id)
        return {item.call_key for item in usage or ()}

    def retry(
        self,
        session_id: str,
        attempt_id: str,
        account: AuthenticatedUser = MENTOR_ACCOUNT,
    ) -> str:
        """Retry a failed attempt over HTTP; returns the new attempt id."""
        with TestClient(
            self.fixture.mentor_app(account),
            headers={'Authorization': 'Bearer test-token'},
        ) as client:
            response = client.post(
                f'/intelligence/mentor-sessions/{session_id}/responses/{attempt_id}/retry',
                json={'submission_key': str(uuid4())},
            )
        assert response.status_code == 202, response.text
        return str(response.json()['attempt_id'])

    def delete_session(
        self, session_id: str, account: AuthenticatedUser = MENTOR_ACCOUNT
    ) -> None:
        access = Mock(spec=MentorAccessProvider)
        access.authorize.side_effect = grant
        RemoveMentorSessionUseCase(
            self.fixture.database, SystemClockProvider(), access
        ).execute(account.account_id, session_id)

    def submit_with_attachment(
        self, account: AuthenticatedUser = MENTOR_ACCOUNT
    ) -> tuple[str, str, str, str]:
        """A session whose first message asks about one ready text attachment.

        Returns the session, attempt, attachment and chunk ids.
        """
        storage = MentorAttachmentStorageStub()
        app = self.fixture.mentor_app(account)
        app.dependency_overrides[FileStoragePipe.get_file_storage_provider] = lambda: (
            storage
        )
        app.dependency_overrides[
            IntelligencePipe.get_mentor_attachment_extractor_provider
        ] = MentorAttachmentExtractorStub
        with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
            batch = client.post('/intelligence/mentor-attachment-batches', json={})
            assert batch.status_code == 201, batch.text
            batch_id = str(batch.json()['batch_id'])
            upload = client.post(
                f'/intelligence/mentor-attachment-batches/{batch_id}/attachments',
                data={'upload_key': str(uuid4())},
                files={'file': ('notes.txt', CHUNK_TEXT.encode(), 'text/plain')},
            )
            assert upload.status_code == 201, upload.text
            attachment_id = str(upload.json()['attachment_id'])
            chunk_id = self.mark_ready(attachment_id)
            created = client.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': str(uuid4()),
                    'first_message': ATTACHMENT_QUESTION,
                    'attachment_batch_id': batch_id,
                    'attachment_ids': [attachment_id],
                },
            )
            assert created.status_code == 201, created.text
        body = created.json()
        return (
            str(body['session']['id']),
            str(body['response']['attempt_id']),
            attachment_id,
            chunk_id,
        )

    def mark_ready(self, attachment_id: str) -> str:
        """Seed the persisted result of preparation: one text chunk, status ready."""
        with self.fixture.database.transaction() as repositories:
            attachment = repositories.mentor_attachments.find_by_id(attachment_id)
            assert attachment is not None
            chunk = MentorAttachmentChunk(
                chunk_id=SystemIdentifierProvider().generate(),
                attachment_id=attachment.id,
                generation=attachment.generation,
                page_number=None,
                locator='chars:1-55#1',
                content=CHUNK_TEXT,
            )
            extraction = MentorAttachmentExtraction(
                chunks=(chunk,),
                analyzed_pages=(),
                illegible_pages=(),
                uninterpreted_pages=(),
            )
            attachment.apply_extraction(extraction, MentorAttachmentStatus.READY)
            repositories.mentor_attachments.update(attachment)
            repositories.mentor_attachment_chunks.add_many((chunk,))
        return chunk.chunk_id

    def cancel(self, attempt_id: str) -> None:
        with self.fixture.database.transaction() as repositories:
            attempts = repositories.mentor_response_attempts
            attempt = attempts.find_by_id_for_update(attempt_id)
            assert attempt is not None
            assert attempts.transition(
                attempt_id,
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.CANCELLED,
                attempt.access_revision,
            )


def build_harness(
    fixture: IntelligenceFixture, redis_fixture: RedisFixture, *, limit_per_hour: int
) -> Harness:
    database = fixture.database
    clock = SystemClockProvider()
    identifiers = SystemIdentifierProvider()
    access = Mock(spec=MentorAccessProvider)
    access.authorize.side_effect = grant
    context = Mock(spec=MentorContextProvider)
    context.read.side_effect = empty_context
    catalog = Mock(spec=MentorCatalogProvider)
    catalog.read_projection.return_value = ()
    catalog.is_diagnostic_activity.return_value = False
    catalog.search.return_value = ()
    route = Mock(spec=MentorRouteProvider)
    route.route.side_effect = unanswered_route
    summarizer = Mock(spec=MentorConversationSummarizerProvider)
    analyzer = Mock(spec=LearnerMemoryAnalyzerProvider)
    analyzer.analyze.return_value = LearnerMemoryAnalysis(
        statements=(), sentence_count=1
    )
    analyzer.concepts.return_value = ()
    similarity = Mock(spec=LearnerMemorySimilarityProvider)
    similarity.similarity.return_value = 0.0
    telemetry = Mock(spec=MentorTelemetryProvider)
    telemetry.scope.return_value = nullcontext()
    limit: MentorGenerationLimitProvider = (
        RedisMentorGenerationLimitProvider(redis_fixture.client, limit_per_hour)
        if limit_per_hour > 0
        else UnavailableMentorGenerationLimitProvider()
    )
    resources = LearnerMemoryResources()

    writer = Mock(spec=MentorWriterAgent)
    writer.general_input.side_effect = MentorWriterAgent.general_input
    writer.run.return_value = written(FIRST_ANSWER)
    reviewer = Mock(spec=MentorReviewerAgent)
    reviewer.review.side_effect = ScriptedReviewer((True,))
    attachment_answer = Mock(spec=MentorAttachmentAnswerAgent)
    attachment_answer.domain_sources.side_effect = (
        MentorAttachmentAnswerAgent.domain_sources
    )

    record_progress = RecordMentorResponseProgressUseCase(database, clock, access)
    renew_claim = RenewMentorResponseClaimUseCase(database, clock, access)
    workflow = AgnoProcessMentorResponseWorkflow(
        summarize_use_case=SummarizeMentorSessionContextUseCase(
            database,
            summarizer,
            access,
            clock,
            identifiers,
            record_progress,
            renew_claim,
            telemetry,
        ),
        update_memories_use_case=UpdateLearnerMemoriesUseCase(
            database,
            analyzer,
            similarity,
            access,
            clock,
            identifiers,
            resources.manifest.update_threshold,
        ),
        prepare_use_case=PrepareMentorResponseUseCase(
            database,
            clock,
            access,
            context,
            route,
            catalog,
            GetMentorAttachmentContextUseCase(database, identifiers, access),
            similarity,
            resources.manifest.relevance_threshold,
            limit,
        ),
        publish_block_use_case=PublishMentorResponseBlockUseCase(
            database, clock, access, context
        ),
        assert_current_use_case=AssertMentorResponseCurrentUseCase(
            database, clock, access
        ),
        renew_claim_use_case=renew_claim,
        release_claim_use_case=ReleaseMentorResponseClaimUseCase(database),
        fail_use_case=FailMentorResponseUseCase(database, clock, access),
        record_usage_use_case=RecordMentorInferenceUsageUseCase(
            database, clock, access, telemetry
        ),
        record_progress_use_case=record_progress,
        writer_agent=writer,
        attachment_answer_agent=attachment_answer,
        reviewer_agent=reviewer,
        finalizer=FinalizeMentorResponseUseCase(database, identifiers, clock, access),
        identifier_provider=identifiers,
        handoffs=AgentOSHandoffStore(),
        telemetry=telemetry,
    )
    return Harness(
        fixture,
        workflow,
        writer,
        reviewer,
        attachment_answer,
        route,
        limit,
        context,
        catalog,
    )


@pytest.fixture
def harness(
    intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
) -> Harness:
    return build_harness(intelligence_fixture, redis_fixture, limit_per_hour=30)


def block_keys(snapshot: MentorResponseSnapshot) -> list[str]:
    return [block.block_key for block in snapshot.blocks]


class TestAgnoProcessMentorResponseWorkflow:
    def test_publishes_the_answer_approved_on_the_first_version(
        self, harness: Harness, redis_fixture: RedisFixture
    ) -> None:
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == ['generated-0']
        assert snapshot.blocks[0].content == FIRST_ANSWER
        assert harness.usage_keys(attempt_id) == {
            'generated-0:writer:0',
            'generated-0:review:0',
        }
        assert harness.reviewer.review.call_count == 1
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        assert redis_fixture.client.zcard(key) == 1  # pyright: ignore[reportUnknownMemberType]

    def test_publishes_the_second_version_after_one_rejection(
        self, harness: Harness
    ) -> None:
        session_id, attempt_id = harness.submit()
        harness.writer.run.side_effect = [
            written(FIRST_ANSWER),
            written(SECOND_ANSWER, tokens=22),
        ]
        harness.reviewer.review.side_effect = ScriptedReviewer((False, True))

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == ['generated-0']
        assert snapshot.blocks[0].content == SECOND_ANSWER
        second_request: MentorGenerationRequest = (
            harness.writer.general_input.call_args_list[1].args[0]
        )
        assert second_request.correction == 'Revise a resposta: fact_fidelity'
        assert harness.usage_keys(attempt_id) == {
            'generated-0:writer:0',
            'generated-0:review:0',
            'generated-1:writer:0',
            'generated-1:review:0',
        }

    def test_publishes_the_abstention_after_two_rejections(
        self, harness: Harness
    ) -> None:
        session_id, attempt_id = harness.submit()
        harness.reviewer.review.side_effect = ScriptedReviewer((False,))

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == [ABSTENTION_KEY]
        assert snapshot.blocks[0].content == ABSTENTION_TEXT
        assert harness.writer.run.call_count == 2
        assert harness.reviewer.review.call_count == 2

    def test_keeps_the_abstention_local_when_the_hourly_limit_is_reached(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=1)
        session_id, attempt_id = harness.submit()
        # Another attempt of the same account already took the only slot.
        assert harness.limit.try_acquire(
            MENTOR_ACCOUNT.account_id, '01J00000000000000000000001'
        )

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == [ABSTENTION_KEY]
        harness.writer.run.assert_not_called()
        harness.reviewer.review.assert_not_called()
        assert harness.usage_keys(attempt_id) == set()

    def test_counts_the_hourly_limit_per_account(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=1)
        first_session, first_attempt = harness.submit()
        other_session, other_attempt = harness.submit(OTHER_ACCOUNT)

        harness.run(first_attempt)
        harness.run(other_attempt)

        assert block_keys(harness.snapshot(first_session)) == ['generated-0']
        assert block_keys(harness.snapshot(other_session, OTHER_ACCOUNT)) == [
            'generated-0'
        ]
        assert harness.writer.run.call_count == 2

    def test_fails_closed_when_the_writer_raises(self, harness: Harness) -> None:
        session_id, attempt_id = harness.submit()
        harness.writer.run.side_effect = RuntimeError('model endpoint down')

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.FAILED
        assert snapshot.status is MentorResponseStatus.FAILED
        assert snapshot.blocks == ()
        harness.reviewer.review.assert_not_called()

    def test_publishes_nothing_generated_when_cancelled_during_review(
        self, harness: Harness
    ) -> None:
        session_id, attempt_id = harness.submit()

        harness.reviewer.review.side_effect = ScriptedReviewer(
            (True,), before=lambda: harness.cancel(attempt_id)
        )

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is not MentorResponseStatus.COMPLETED
        assert 'generated-0' not in block_keys(snapshot)
        assert all(block.content != FIRST_ANSWER for block in snapshot.blocks)

    def test_does_not_add_the_unavailable_line_to_a_complete_progress_answer(
        self, harness: Harness
    ) -> None:
        harness.route.route.side_effect = real_route(
            {'consult_progress': 0.93, 'consult_gamification': 0.89},
            progress_context(
                ('goals', 'Aprender a programar'),
                (
                    'progress_overview',
                    'Aprender a programar: 1 Habilidade — 1 não iniciada.',
                ),
            ),
        )
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert [block.content for block in snapshot.blocks] == [
            (
                'Progresso:\n- Aprender a programar: 1 Habilidade — 1 não iniciada.\n\n'
                'Diga o nome de um Objetivo para ver as Habilidades dele.'
            )
        ]

    def test_keeps_the_unavailable_line_for_a_gamification_question_without_facts(
        self, harness: Harness
    ) -> None:
        harness.route.route.side_effect = real_route(
            {'consult_gamification': 0.97}, progress_context()
        )
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        contents = [block.content for block in harness.snapshot(session_id).blocks]
        assert contents == [ABSTENTION_TEXT]

    def test_keeps_the_unavailable_line_when_the_missing_fact_is_the_stronger_question(
        self, harness: Harness
    ) -> None:
        harness.route.route.side_effect = real_route(
            {'consult_progress': 0.90, 'consult_gamification': 0.97},
            progress_context(
                ('goals', 'Aprender a programar'),
                (
                    'progress_overview',
                    'Aprender a programar: 1 Habilidade — 1 não iniciada.',
                ),
            ),
        )
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        contents = [block.content for block in harness.snapshot(session_id).blocks]
        assert len(contents) == 2
        assert contents[0].startswith('Progresso:')
        assert contents[1] == ABSTENTION_TEXT

    def test_publishes_a_local_answer_without_taking_a_slot(
        self, harness: Harness, redis_fixture: RedisFixture
    ) -> None:
        harness.route.route.side_effect = local_route
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == ['faq-fractions']
        assert snapshot.blocks[0].content == LOCAL_ANSWER
        harness.writer.run.assert_not_called()
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        assert redis_fixture.client.zcard(key) == 0  # pyright: ignore[reportUnknownMemberType]

    def test_turns_general_answers_off_when_the_limit_is_zero(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=0)
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)

        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(harness.snapshot(session_id)) == [ABSTENTION_KEY]
        harness.writer.run.assert_not_called()
        assert harness.usage_keys(attempt_id) == set()

    def test_frees_an_aged_slot_in_the_window(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=1)
        session_id, attempt_id = harness.submit()
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        # One slot taken more than an hour ago, by the store's own clock.
        server_seconds = int(redis_fixture.client.time()[0])  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        redis_fixture.client.zadd(  # pyright: ignore[reportUnknownMemberType]
            key, {'01J00000000000000000000009': server_seconds - 4000}
        )

        harness.run(attempt_id)

        assert block_keys(harness.snapshot(session_id)) == ['generated-0']
        assert redis_fixture.client.zcard(key) == 1  # pyright: ignore[reportUnknownMemberType]
        assert redis_fixture.client.zscore(key, attempt_id) is not None  # pyright: ignore[reportUnknownMemberType]

    def test_takes_one_slot_for_an_attempt_run_twice(
        self, harness: Harness, redis_fixture: RedisFixture
    ) -> None:
        session_id, attempt_id = harness.submit()

        harness.run(attempt_id)
        harness.run(attempt_id)

        assert block_keys(harness.snapshot(session_id)) == ['generated-0']
        assert harness.writer.run.call_count == 1
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        assert redis_fixture.client.zcard(key) == 1  # pyright: ignore[reportUnknownMemberType]

    def test_keeps_the_failed_attempts_slot_and_gives_its_retry_a_new_one(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=2)
        session_id, attempt_id = harness.submit()
        harness.writer.run.side_effect = RuntimeError('model endpoint down')
        harness.run(attempt_id)
        assert harness.status(attempt_id) is MentorResponseStatus.FAILED
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        assert redis_fixture.client.zcard(key) == 1  # pyright: ignore[reportUnknownMemberType]

        retried_id = harness.retry(session_id, attempt_id)
        harness.writer.run.side_effect = None
        harness.run(retried_id)

        snapshot = harness.snapshot(session_id)
        assert snapshot.attempt_id == retried_id
        assert harness.status(retried_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == ['generated-0']
        assert snapshot.blocks[0].content == FIRST_ANSWER
        assert redis_fixture.client.zcard(key) == 2  # pyright: ignore[reportUnknownMemberType]
        assert harness.usage_keys(retried_id) == {
            'generated-0:writer:0',
            'generated-0:review:0',
        }

    def test_publishes_nothing_generated_when_the_conversation_is_deleted_during_review(
        self, harness: Harness
    ) -> None:
        session_id, attempt_id = harness.submit()
        harness.reviewer.review.side_effect = ScriptedReviewer(
            (True,), before=lambda: harness.delete_session(session_id)
        )

        harness.run(attempt_id)

        with harness.fixture.database.transaction() as repositories:
            assert repositories.mentor_response_attempts.find_by_id(attempt_id) is None
            assert (
                repositories.mentor_response_events.snapshot(
                    MENTOR_ACCOUNT.account_id, session_id
                )
                is None
            )
            assert (
                repositories.mentor_messages.find_all(
                    MENTOR_ACCOUNT.account_id, session_id
                )
                == ()
            )

    def test_answers_an_attachment_question_outside_the_limit(
        self, intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
    ) -> None:
        # The only general slot is already taken; attachment answers are outside it.
        harness = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=1)
        assert harness.limit.try_acquire(
            MENTOR_ACCOUNT.account_id, '01J00000000000000000000001'
        )
        session_id, attempt_id, attachment_id, chunk_id = (
            harness.submit_with_attachment()
        )
        harness.attachment_answer.answer.side_effect = attachment_answer(
            attachment_id, chunk_id
        )
        harness.route.route.side_effect = attachment_route

        harness.run(attempt_id)

        snapshot = harness.snapshot(session_id)
        assert harness.status(attempt_id) is MentorResponseStatus.COMPLETED
        assert block_keys(snapshot) == ['generated-0']
        assert snapshot.blocks[0].content == ATTACHMENT_ANSWER
        assert [source.chunk_id for source in snapshot.blocks[0].sources] == [chunk_id]
        harness.writer.run.assert_not_called()
        assert harness.usage_keys(attempt_id) == {
            'generated-0:attachment-answer:0',
            'generated-0:review:0',
        }
        key = RedisMentorGenerationLimitProvider.key_for(MENTOR_ACCOUNT.account_id)
        assert redis_fixture.client.zcard(key) == 1  # pyright: ignore[reportUnknownMemberType]


PROGRESS = 'Qual é meu progresso no Objetivo?'
COMPLETED = 'Quais Habilidades já concluí?'
CLOSING = 'Diga o nome de um Objetivo para ver as Habilidades dele.'
NO_GOALS = (
    'Você ainda não tem Objetivos. Crie um na tela inicial para acompanhar '
    'seu progresso.'
)
FRACTIONS_LIST = (
    'Progresso no Objetivo Estudar frações:\n'
    '- Frações equivalentes: concluída\n'
    '- Comparar frações: em aprendizado\n'
    '- Somar frações: não iniciada'
)
PROGRESS_SIMILARITIES = {'consult_progress': 0.95}
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
STATUS = SkillExperienceStatus


def skill(name: str) -> Skill:
    return SkillFaker.fake(name=name)


def goal(account_id: str, title: str, days: int) -> Goal:
    moment = BASE_TIME + timedelta(days=days)
    return GoalFaker.fake(
        account_id=account_id, title=title, created_at=moment, updated_at=moment
    )


def experience(
    owner: Goal, learned: Skill | None, status: SkillExperienceStatus, position: int
) -> SkillExperience:
    return SkillExperienceFaker.fake(
        goal_id=owner.id,
        skill_id=learned.id if learned is not None else None,
        status=status,
        created_at=BASE_TIME + timedelta(minutes=position),
    )


def persist(
    harness: Harness,
    *,
    skills: list[Skill],
    goals: list[Goal],
    experiences: list[SkillExperience],
) -> None:
    engine = harness.fixture.postgres.engine
    with SqlalchemyCurriculumDatabase(engine).transaction() as repositories:
        repositories.skills.add_many(skills)
    with SqlalchemyLearningDatabase(engine).transaction() as repositories:
        repositories.goals.add_many(goals)
        repositories.skill_experiences.add_many(experiences)


def seed_full_account(harness: Harness) -> dict[str, Goal]:
    """Three Objetivos: mixed statuses, a nameless completion and an empty one."""
    account_id = MENTOR_ACCOUNT.account_id
    equivalent = skill('Frações equivalentes')
    compare = skill('Comparar frações')
    add = skill('Somar frações')
    angles = skill('Ângulos')
    triangles = skill('Triângulos')
    fractions = goal(account_id, 'Estudar frações', 30)
    geometry = goal(account_id, 'Geometria básica', 20)
    empty = goal(account_id, 'Objetivo vazio', 10)
    persist(
        harness,
        skills=[equivalent, compare, add, angles, triangles],
        goals=[fractions, geometry, empty],
        experiences=[
            experience(fractions, equivalent, STATUS.COMPLETED, 1),
            experience(fractions, compare, STATUS.LEARNING, 2),
            experience(fractions, add, STATUS.NOT_STARTED, 3),
            experience(geometry, angles, STATUS.DIAGNOSING, 1),
            experience(geometry, triangles, STATUS.COMPLETED, 2),
            # A completed Habilidade that the Curriculum catalog does not know.
            experience(geometry, None, STATUS.COMPLETED, 3),
        ],
    )
    return {'fractions': fractions, 'geometry': geometry, 'empty': empty}


@pytest.fixture
def progress_harness(
    intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
) -> Harness:
    """The workflow over the real local route and the real Learning context."""
    built = build_harness(intelligence_fixture, redis_fixture, limit_per_hour=30)
    built.use_learning_data()
    built.route.route.side_effect = real_route(PROGRESS_SIMILARITIES)
    return built


class TestAgnoProcessMentorResponseWorkflowProgress:
    """Local progress answers from the learner's own data, with no model call."""

    def test_answers_with_an_overview_of_all_goals_when_no_goal_is_resolved(
        self, progress_harness: Harness
    ) -> None:
        seed_full_account(progress_harness)

        _, answer = progress_harness.ask(PROGRESS)

        assert answer == (
            'Progresso:\n'
            '- Estudar frações: 3 Habilidades — 1 não iniciada, 1 em aprendizado, '
            '1 concluída.\n'
            '- Geometria básica: 3 Habilidades — 1 em diagnóstico, 2 concluídas.\n'
            '- Objetivo vazio: nenhuma Habilidade ainda.\n\n'
            'Habilidades concluídas: Frações equivalentes (Objetivo Estudar frações)\n'
            'Triângulos (Objetivo Geometria básica)\n'
            'Habilidade sem título (Objetivo Geometria básica)\n\n'
            f'{CLOSING}'
        )
        progress_harness.assert_no_model_call()

    def test_lists_the_skills_of_a_goal_named_in_the_message(
        self, progress_harness: Harness
    ) -> None:
        seed_full_account(progress_harness)

        _, answer = progress_harness.ask('Qual é meu progresso em Estudar frações?')

        assert answer == FRACTIONS_LIST
        progress_harness.assert_no_model_call()

    def test_keeps_the_clarification_when_two_goals_share_the_title(
        self, progress_harness: Harness
    ) -> None:
        account_id = MENTOR_ACCOUNT.account_id
        first = goal(account_id, 'Álgebra', 20)
        second = goal(account_id, 'Álgebra', 10)
        equations = skill('Equações')
        persist(
            progress_harness,
            skills=[equations],
            goals=[first, second],
            experiences=[experience(first, equations, STATUS.LEARNING, 1)],
        )

        _, answer = progress_harness.ask('Qual é meu progresso em Álgebra?')

        assert 'Equações' not in answer
        assert answer.startswith('Encontrei mais de um Objetivo com esse nome')
        progress_harness.assert_no_model_call()

    def test_resolves_the_goal_from_a_page_hint_and_from_conversation_continuity(
        self, progress_harness: Harness
    ) -> None:
        goals = seed_full_account(progress_harness)

        _, from_hint = progress_harness.ask(
            PROGRESS, {'goal_id': goals['fractions'].id}
        )
        session_id, _ = progress_harness.ask('Qual é meu progresso em Estudar frações?')
        follow_up = progress_harness.submit_follow_up(session_id, PROGRESS)
        from_continuity = progress_harness.answer(session_id, follow_up)
        _, fresh = progress_harness.ask(PROGRESS)

        assert from_hint == FRACTIONS_LIST
        assert from_continuity == FRACTIONS_LIST
        assert fresh.startswith('Progresso:\n- Estudar frações: 3 Habilidades')
        progress_harness.assert_no_model_call()

    def test_says_that_a_goal_without_skills_has_none(
        self, progress_harness: Harness
    ) -> None:
        seed_full_account(progress_harness)

        _, answer = progress_harness.ask('Qual é meu progresso em Objetivo vazio?')

        assert answer == (
            'Progresso no Objetivo Objetivo vazio:\n'
            '- Este Objetivo ainda não tem Habilidades.'
        )
        progress_harness.assert_no_model_call()

    def test_shows_completed_skills_by_name_and_keeps_the_selected_skill_summary(
        self, progress_harness: Harness
    ) -> None:
        goals = seed_full_account(progress_harness)
        learning = SqlalchemyLearningDatabase(progress_harness.fixture.postgres.engine)
        with learning.transaction() as repositories:
            selected = repositories.skill_experiences.find_many_by_goal_id(
                goals['fractions'].id
            )[1]

        _, completed = progress_harness.ask(COMPLETED)
        _, summary = progress_harness.ask(
            'Qual é meu progresso nesta Habilidade?',
            {'goal_id': goals['fractions'].id, 'skill_id': selected.skill_id or ''},
        )

        names = (
            'Frações equivalentes (Objetivo Estudar frações)\n'
            'Triângulos (Objetivo Geometria básica)\n'
            'Habilidade sem título (Objetivo Geometria básica)'
        )
        assert names in completed
        assert summary.startswith(
            f'Progresso: Habilidade: em aprendizado\n\nHabilidades concluídas: {names}'
        )
        assert (selected.skill_id or '') not in completed + summary
        progress_harness.assert_no_model_call()

    def test_bounds_every_list_to_twenty_items_with_the_exact_remainder(
        self, progress_harness: Harness
    ) -> None:
        account_id = MENTOR_ACCOUNT.account_id
        goals = [
            goal(account_id, f'Objetivo {index:02d}', 100 - index)
            for index in range(23)
        ]
        skills = [skill(f'Habilidade {index:02d}') for index in range(22)]
        persist(
            progress_harness,
            skills=skills,
            goals=goals,
            experiences=[
                experience(goals[0], learned, STATUS.COMPLETED, index)
                for index, learned in enumerate(skills)
            ],
        )

        _, overview = progress_harness.ask(PROGRESS)
        _, listed = progress_harness.ask('Qual é meu progresso em Objetivo 00?')

        overview_lines = overview.split('\n\n')[0].splitlines()
        assert overview_lines[0] == 'Progresso:'
        assert len(overview_lines) == 1 + 20 + 1
        assert overview_lines[-1] == '- e mais 3.'
        completed = overview.split('\n\n')[1].splitlines()
        assert len(completed) == 20 + 1
        assert completed[-1] == 'e mais 2.'
        assert completed[0].startswith('Habilidades concluídas: Habilidade 00 (')
        listed_lines = listed.splitlines()
        assert listed_lines[0] == 'Progresso no Objetivo Objetivo 00:'
        assert len(listed_lines) == 1 + 20 + 1
        assert listed_lines[-1] == '- e mais 2.'
        progress_harness.assert_no_model_call()

    def test_says_there_are_no_goals_and_keeps_the_unavailable_text_elsewhere(
        self, progress_harness: Harness
    ) -> None:
        _, progress = progress_harness.ask(PROGRESS)
        progress_harness.route.route.side_effect = real_route(
            {'consult_gamification': 0.97}
        )
        _, gamification = progress_harness.ask('Quantos pontos de XP eu tenho?')

        assert progress == NO_GOALS
        assert gamification == ABSTENTION_TEXT
        progress_harness.assert_no_model_call()

    def test_shows_only_the_status_of_a_diagnosing_skill_and_never_another_account(
        self, progress_harness: Harness
    ) -> None:
        account_id = MENTOR_ACCOUNT.account_id
        diagnosing = skill('Ângulos')
        other_skill = skill('Habilidade secreta')
        competency = CompetencyFaker.fake(skill_id=diagnosing.id, name='Medir ângulos')
        activity = ActivityFaker.fake(
            competency_id=competency.id,
            activity_type=ActivityType.DIAGNOSTIC,
            title='Pergunta diagnóstica sigilosa',
        )
        diagnosing.initial_diagnostic_activity_ids = (activity.id,)
        geometry = goal(account_id, 'Geometria básica', 20)
        foreign = goal(OTHER_ACCOUNT.account_id, 'Objetivo alheio', 30)
        engine = progress_harness.fixture.postgres.engine
        with SqlalchemyCurriculumDatabase(engine).transaction() as repositories:
            repositories.skills.add_many([diagnosing, other_skill])
            repositories.competencies.add_many([competency])
            repositories.activities.add_many([activity])
        with SqlalchemyLearningDatabase(engine).transaction() as repositories:
            repositories.goals.add_many([geometry, foreign])
            repositories.skill_experiences.add_many(
                [
                    experience(geometry, diagnosing, STATUS.DIAGNOSING, 1),
                    experience(foreign, other_skill, STATUS.COMPLETED, 1),
                ]
            )

        _, overview = progress_harness.ask(PROGRESS)
        _, listed = progress_harness.ask('Qual é meu progresso em Geometria básica?')

        assert overview == (
            'Progresso:\n- Geometria básica: 1 Habilidade — 1 em diagnóstico.\n\n'
            f'{CLOSING}'
        )
        assert listed == (
            'Progresso no Objetivo Geometria básica:\n'
            '- Ângulos: diagnóstico em andamento'
        )
        for forbidden in ('sigilosa', 'Medir', 'alheio', 'secreta'):
            assert forbidden not in overview + listed
        progress_harness.assert_no_model_call()

    def test_fails_recoverably_when_learning_cannot_be_read_and_answers_on_retry(
        self, progress_harness: Harness
    ) -> None:
        seed_full_account(progress_harness)
        read = progress_harness.context.read.side_effect
        failures = [ServiceUnavailableError('Learning indisponível.')]

        def flaky(*args: object, **kwargs: object) -> MentorContextSnapshot:
            if failures:
                raise failures.pop()
            return read(*args, **kwargs)

        progress_harness.context.read.side_effect = flaky
        session_id, attempt_id = progress_harness.submit_message(PROGRESS)

        progress_harness.run(attempt_id)

        assert progress_harness.status(attempt_id) is MentorResponseStatus.FAILED
        assert progress_harness.snapshot(session_id).blocks == ()
        retry_id = progress_harness.retry(session_id, attempt_id)
        answer = progress_harness.answer(session_id, retry_id)
        assert answer.startswith('Progresso:\n- Estudar frações: 3 Habilidades')
        assert ABSTENTION_TEXT not in answer
        assert 'Learning indisponível' not in answer
        progress_harness.assert_no_model_call()
