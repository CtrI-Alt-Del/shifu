"""Intelligence-owned workflow registrations and AgentOS lifecycle."""

from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, cast

import httpx
from redis import Redis

from shifu.intelligence.ai.agno.agents import (
    MentorAttachmentAnswerAgent,
    MentorAttachmentVisionAgent,
    MentorReviewerAgent,
    MentorTitleAgent,
    MentorWriterAgent,
)
from shifu.intelligence.ai.agno.workflows import (
    AgnoGenerateMentorTitleWorkflow,
    AgnoPrepareMentorAttachmentWorkflow,
    AgnoProcessMentorResponseWorkflow,
    AgnoPurgeMentorAttachmentsWorkflow,
)
from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources
from shifu.intelligence.core.use_cases import (
    AssertMentorResponseCurrentUseCase,
    CompleteMentorAttachmentUseCase,
    FailMentorAttachmentUseCase,
    FailMentorResponseUseCase,
    PrepareMentorAttachmentUseCase,
    PrepareMentorResponseUseCase,
    PublishMentorResponseBlockUseCase,
    PurgeLearnerMemoriesForAccountUseCase,
    PurgeMentorActionProposalsForAccountUseCase,
    PurgeMentorAttachmentsUseCase,
    PurgeMentorSummariesForAccountUseCase,
    RecordMentorActionOutcomeUseCase,
    RecordMentorInferenceUsageUseCase,
    RecordMentorResponseProgressUseCase,
    ReleaseMentorAttachmentClaimUseCase,
    ReleaseMentorResponseClaimUseCase,
    RenewMentorAttachmentClaimUseCase,
    RenewMentorResponseClaimUseCase,
    SummarizeMentorSessionContextUseCase,
    UpdateLearnerMemoriesUseCase,
)
from shifu.intelligence.core.use_cases.finalize_mentor_response_use_case import (
    FinalizeMentorResponseUseCase,
)
from shifu.intelligence.core.use_cases.get_mentor_attachment_context_use_case import (
    GetMentorAttachmentContextUseCase,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.providers.code_rubric_assessor.jev.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.intelligence.providers.generation_limit.redis.redis_mentor_generation_limit_provider import (
    RedisMentorGenerationLimitProvider,
)
from shifu.intelligence.providers.generation_limit.unavailable_mentor_generation_limit_provider import (
    UnavailableMentorGenerationLimitProvider,
)
from shifu.intelligence.providers.mentor_attachment_extraction.local.local_mentor_attachment_extractor_provider import (
    LocalMentorAttachmentExtractorProvider,
)
from shifu.intelligence.providers.memory_classification.tfidf.tfidf_learner_memory_analyzer_provider import (
    TfidfLearnerMemoryAnalyzerProvider,
)
from shifu.intelligence.providers.mentor_title.unavailable_generate_mentor_title_provider import (
    UnavailableGenerateMentorTitleProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.intelligence.providers.routing.lazy.lazy_mentor_route_provider import (
    LazyMentorRouteProvider,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter.jev_planning_intent_classifier_provider import (
    JevPlanningIntentClassifierProvider,
)
from shifu.intelligence.providers.planning.lazy_planning_skill_retrieval_provider import (
    LazyPlanningSkillRetrievalProvider,
)
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.errors import PlanningIndexUnavailableError
from shifu.intelligence.providers.summarization.textrank.textrank_mentor_conversation_summarizer_provider import (
    TextrankMentorConversationSummarizerProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.intelligence.providers.text_similarity.bag_of_words.bag_of_words_learner_memory_similarity_provider import (
    BagOfWordsLearnerMemorySimilarityProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.messaging.agentos.agentos_runtime import AgentOSRuntime
from shifu.shared.messaging.agentos.agentos_settings import AgentOSQueueSettings
from shifu.shared.pipes.file_storage_pipe import FileStoragePipe
from shifu.shared.providers.langfuse_telemetry_provider import LangfuseTelemetryProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from langfuse import Langfuse
    from sqlalchemy.engine import Engine

    from shifu.intelligence.core.domain.structures import (
        MentorInferenceUsage,
        PlanningQuery,
        PlanningSkillRanking,
    )
    from shifu.intelligence.core.interfaces import (
        GenerateMentorTitleProvider,
        IntelligenceDatabase,
        LearnerMemoryAnalyzerProvider,
        LearnerMemorySimilarityProvider,
        MentorConversationSummarizerProvider,
        MentorEmbeddingsProvider,
        MentorGenerationLimitProvider,
        MentorRouteProvider,
        MentorTelemetryProvider,
        PlanningIntentClassifierProvider,
        PlanningSkillRetrievalProvider,
    )
    from shifu.shared.core.interfaces import (
        CodeRubricAssessorProvider,
        CurriculumCatalogProvider,
        FileStorageProvider,
        MentorAccessProvider,
        MentorCatalogProvider,
        MentorContextProvider,
        MentorGoalDestinationsProvider,
        OutboxEvent,
    )
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.settings import Settings


_MENTOR_EVENT = 'intelligence/mentor.response.requested'
_ATTACHMENT_PREPARE_EVENT = 'intelligence/mentor-attachment.preparation.requested'
_ATTACHMENT_CLEANUP_EVENT = 'intelligence/mentor-attachment.cleanup.requested'


class _UnavailableTitleAgent:
    def run(self, _input: str) -> object:
        raise ServiceUnavailableError('Mentor title generation is unavailable.')


class _UnavailableVisionAgent:
    def analyze(
        self,
        _image_content: bytes,
        *,
        media_type: str,
        attachment_id: str,
        page_number: int,
        usage_recorder: object = None,
    ) -> object:
        del media_type, attachment_id, page_number, usage_recorder
        raise ServiceUnavailableError('Mentor attachment vision is unavailable.')


class _UnavailableWriterAgent:
    def run(self, **_kwargs: object) -> object:
        raise ServiceUnavailableError('Mentor response generation is unavailable.')

    def general_input(self, *_args: object, **_kwargs: object) -> str:
        raise ServiceUnavailableError('Mentor response generation is unavailable.')


class _UnavailableAttachmentAnswerAgent:
    def answer(self, *_args: object, **_kwargs: object) -> object:
        raise ServiceUnavailableError('Mentor attachment answers are unavailable.')


class _UnavailableReviewerAgent:
    def review(self, *_args: object, **_kwargs: object) -> object:
        raise ServiceUnavailableError('Mentor response review is unavailable.')


class _UnavailablePlanningSkillRetrievalProvider:
    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        del query
        raise PlanningIndexUnavailableError


class _LazyEmbeddingsProvider:
    """Load the pinned local E5 model once, on first use, behind the embeddings port."""

    def __init__(self) -> None:
        self._lock: Lock = Lock()
        self._provider: MentorEmbeddingsProvider | None = None

    def embed_queries(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return self._loaded().embed_queries(texts)

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return self._loaded().embed_passages(texts)

    def _loaded(self) -> MentorEmbeddingsProvider:
        with self._lock:
            if self._provider is None:
                from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
                    SentenceTransformersEmbeddingsProvider,
                )

                try:
                    self._provider = SentenceTransformersEmbeddingsProvider()
                except (OSError, ValueError) as error:
                    raise ServiceUnavailableError(
                        'O índice local do Mentor está indisponível.'
                    ) from error
            return self._provider


class IntelligenceWorkflowsRegistry:
    """Own Intelligence workflow IDs, providers, queue and runtime resources."""

    MODULE_ID: ClassVar[str] = 'intelligence'

    def __init__(
        self,
        settings: Settings,
        observability: LangfuseTelemetryProvider | None,
        access_provider: MentorAccessProvider,
        context_provider: MentorContextProvider,
        catalog_provider: MentorCatalogProvider,
        mentor_goal_destinations_provider: MentorGoalDestinationsProvider,
        *,
        outbox_engine: Engine,
        telemetry_client: Langfuse | None = None,
        route_provider: MentorRouteProvider | None = None,
        telemetry: MentorTelemetryProvider | None = None,
        curriculum_catalog_provider: CurriculumCatalogProvider | None = None,
        summarizer: MentorConversationSummarizerProvider | None = None,
        learner_memory_analyzer: LearnerMemoryAnalyzerProvider | None = None,
    ) -> None:
        observability = observability or LangfuseTelemetryProvider(
            'intelligence', telemetry_client
        )
        self._settings = settings
        self._engine = outbox_engine
        self._database: IntelligenceDatabase = IntelligencePipe.create_database(
            outbox_engine
        )
        self._identifier_provider = SystemIdentifierProvider()
        self._clock_provider = SystemClockProvider()
        self._access_provider = access_provider
        self._context_provider = context_provider
        self._catalog_provider = catalog_provider
        self._telemetry: MentorTelemetryProvider = telemetry or (
            LangfuseMentorTelemetryProvider(observability)
        )
        # One lazily loaded spaCy pipeline and one E5 model serve routing and
        # summarization; neither is read from disk until a request needs it.
        self._shared_preprocessor = SpacyMentorTextPreprocessorProvider(lazy=True)
        self._shared_embeddings: MentorEmbeddingsProvider = _LazyEmbeddingsProvider()
        self._route_provider = (
            route_provider
            if route_provider is not None
            else LazyMentorRouteProvider(
                self._database,
                catalog_provider,
                self._telemetry,
                preprocessor=self._shared_preprocessor,
                embeddings=self._shared_embeddings,
            )
        )
        self._summarizer_provider: MentorConversationSummarizerProvider = (
            summarizer
            if summarizer is not None
            else TextrankMentorConversationSummarizerProvider(
                self._shared_preprocessor, self._shared_embeddings
            )
        )
        # The classifier fits lazily on its first analysis, inside the AgentOS step;
        # building the registry reads only the small versioned JSON resources.
        self._memory_resources = LearnerMemoryResources()
        self._learner_memory_analyzer_provider: LearnerMemoryAnalyzerProvider = (
            learner_memory_analyzer
            if learner_memory_analyzer is not None
            else TfidfLearnerMemoryAnalyzerProvider(
                self._shared_preprocessor, self._memory_resources
            )
        )
        self._learner_memory_similarity_provider: LearnerMemorySimilarityProvider = (
            BagOfWordsLearnerMemorySimilarityProvider(
                self._shared_preprocessor, self._memory_resources
            )
        )
        self._handoffs = AgentOSHandoffStore()
        self._storage_provider = FileStoragePipe.create_file_storage_provider(settings)
        self._extractor_provider = LocalMentorAttachmentExtractorProvider(
            settings, self._identifier_provider
        )

        title_agent = (
            MentorTitleAgent()
            if MentorTitleAgent.enabled()
            else cast('MentorTitleAgent', _UnavailableTitleAgent())
        )
        title_workflow = AgnoGenerateMentorTitleWorkflow(
            title_agent, self._handoffs, observability
        )

        vision_agent = (
            MentorAttachmentVisionAgent()
            if MentorAttachmentVisionAgent.enabled()
            else cast('MentorAttachmentVisionAgent', _UnavailableVisionAgent())
        )
        prepare_attachment = PrepareMentorAttachmentUseCase(
            self._database,
            self._clock_provider,
            access_provider,
            self._storage_provider,
        )
        complete_attachment = CompleteMentorAttachmentUseCase(
            self._database, self._clock_provider, access_provider
        )
        fail_attachment = FailMentorAttachmentUseCase(
            self._database, self._clock_provider, access_provider
        )
        renew_attachment = RenewMentorAttachmentClaimUseCase(
            self._database, self._clock_provider, access_provider
        )
        release_attachment = ReleaseMentorAttachmentClaimUseCase(self._database)
        prepare_workflow = AgnoPrepareMentorAttachmentWorkflow(
            prepare_use_case=prepare_attachment,
            complete_use_case=complete_attachment,
            fail_use_case=fail_attachment,
            renew_claim_use_case=renew_attachment,
            release_claim_use_case=release_attachment,
            extractor_provider=self._extractor_provider,
            vision_agent=vision_agent,
            identifier_provider=self._identifier_provider,
            max_pdf_pages=settings.mentor_attachment_max_pdf_pages,
            usage_recorder=self._record_attachment_usage,
        )
        self._purge_mentor_attachments_use_case = PurgeMentorAttachmentsUseCase(
            self._database, self._clock_provider, self._storage_provider
        )
        purge_workflow = AgnoPurgeMentorAttachmentsWorkflow(
            self._purge_mentor_attachments_use_case
        )

        attachment_context_use_case = GetMentorAttachmentContextUseCase(
            self._database,
            self._identifier_provider,
            access_provider,
        )
        writer_agent = (
            MentorWriterAgent()
            if MentorWriterAgent.enabled()
            else cast('MentorWriterAgent', _UnavailableWriterAgent())
        )
        attachment_answer_agent = (
            MentorAttachmentAnswerAgent()
            if MentorAttachmentAnswerAgent.enabled()
            else cast(
                'MentorAttachmentAnswerAgent', _UnavailableAttachmentAnswerAgent()
            )
        )
        reviewer_agent = (
            MentorReviewerAgent()
            if MentorReviewerAgent.enabled()
            else cast('MentorReviewerAgent', _UnavailableReviewerAgent())
        )
        self._generation_limit_client: Redis | None = None
        generation_limit: MentorGenerationLimitProvider = (
            UnavailableMentorGenerationLimitProvider()
        )
        if (
            MentorWriterAgent.enabled()
            and MentorReviewerAgent.enabled()
            and settings.mentor_generation_limit_per_hour > 0
        ):
            # Short timeouts keep a blackholed store failing closed instead of hanging.
            self._generation_limit_client = Redis.from_url(  # pyright: ignore[reportUnknownMemberType] - redis-py has incomplete stubs.
                settings.redis_url,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            generation_limit = RedisMentorGenerationLimitProvider(
                self._generation_limit_client,
                settings.mentor_generation_limit_per_hour,
            )
        prepare_response = PrepareMentorResponseUseCase(
            self._database,
            self._clock_provider,
            access_provider,
            context_provider,
            self._route_provider,
            catalog_provider,
            attachment_context_use_case,
            self._learner_memory_similarity_provider,
            self._memory_resources.manifest.relevance_threshold,
            generation_limit,
            mentor_goal_destinations_provider,
        )
        publish_response_block = PublishMentorResponseBlockUseCase(
            self._database,
            self._clock_provider,
            access_provider,
            context_provider,
            self._identifier_provider,
        )
        assert_response_current = AssertMentorResponseCurrentUseCase(
            self._database, self._clock_provider, access_provider
        )
        renew_response_claim = RenewMentorResponseClaimUseCase(
            self._database, self._clock_provider, access_provider
        )
        release_response_claim = ReleaseMentorResponseClaimUseCase(self._database)
        fail_response = FailMentorResponseUseCase(
            self._database, self._clock_provider, access_provider
        )
        record_response_usage = RecordMentorInferenceUsageUseCase(
            self._database,
            self._clock_provider,
            access_provider,
            self._telemetry,
        )
        record_response_progress = RecordMentorResponseProgressUseCase(
            self._database, self._clock_provider, access_provider
        )
        summarize_context = SummarizeMentorSessionContextUseCase(
            self._database,
            self._summarizer_provider,
            access_provider,
            self._clock_provider,
            self._identifier_provider,
            record_response_progress,
            renew_response_claim,
            self._telemetry,
        )
        update_memories = UpdateLearnerMemoriesUseCase(
            self._database,
            self._learner_memory_analyzer_provider,
            self._learner_memory_similarity_provider,
            access_provider,
            self._clock_provider,
            self._identifier_provider,
            self._memory_resources.manifest.update_threshold,
        )
        self._purge_mentor_summaries_use_case = PurgeMentorSummariesForAccountUseCase(
            self._database
        )
        self._purge_learner_memories_use_case = PurgeLearnerMemoriesForAccountUseCase(
            self._database
        )
        self._purge_mentor_action_proposals_use_case = (
            PurgeMentorActionProposalsForAccountUseCase(self._database)
        )
        self._record_mentor_action_outcome_use_case = RecordMentorActionOutcomeUseCase(
            self._database, self._clock_provider
        )
        process_workflow = AgnoProcessMentorResponseWorkflow(
            summarize_use_case=summarize_context,
            update_memories_use_case=update_memories,
            prepare_use_case=prepare_response,
            publish_block_use_case=publish_response_block,
            assert_current_use_case=assert_response_current,
            renew_claim_use_case=renew_response_claim,
            release_claim_use_case=release_response_claim,
            fail_use_case=fail_response,
            record_usage_use_case=record_response_usage,
            record_progress_use_case=record_response_progress,
            writer_agent=writer_agent,
            attachment_answer_agent=attachment_answer_agent,
            reviewer_agent=reviewer_agent,
            finalizer=FinalizeMentorResponseUseCase(
                self._database,
                self._identifier_provider,
                self._clock_provider,
                access_provider,
            ),
            identifier_provider=self._identifier_provider,
            handoffs=self._handoffs,
            telemetry=self._telemetry,
        )
        self._workflows = (
            title_workflow,
            process_workflow,
            prepare_workflow,
            purge_workflow,
        )

        self._code_rubric_http_client = self._build_code_rubric_client()
        self._code_rubric_client = self._build_code_rubric_provider(
            settings, self._code_rubric_http_client
        )
        # Planner ports share the decisions client; the index loads on first use only.
        self._planning_intent_classifier: PlanningIntentClassifierProvider = (
            JevPlanningIntentClassifierProvider(
                self._code_rubric_http_client,
                settings.openrouter_api_key,
                str(settings.openrouter_decisions_url),
                settings.jev_model,
                PlannerResources().manifest.intent_thresholds,
            )
        )
        self._planning_skill_retrieval: PlanningSkillRetrievalProvider = (
            LazyPlanningSkillRetrievalProvider(
                self._database, curriculum_catalog_provider
            )
            if curriculum_catalog_provider is not None
            else _UnavailablePlanningSkillRetrievalProvider()
        )
        database_url = settings.agentos_database_url
        self._runtime = (
            AgentOSRuntime(
                module='intelligence',
                agentos_id='shifu-intelligence',
                schema='agentos_intelligence',
                database_url=str(database_url),
                redis_url=settings.redis_url,
                queue_settings=AgentOSQueueSettings.for_module(
                    'intelligence', settings
                ),
                workflows=self._workflows,
                workflow_event_projector=self._project_event,
                outbox_engine=outbox_engine,
                observability=observability,
            )
            if database_url is not None
            else None
        )
        self._observability_provider = (
            self._runtime.observability if self._runtime is not None else observability
        )
        if isinstance(self._telemetry, LangfuseMentorTelemetryProvider):
            self._telemetry.bind(self._observability_provider)
        if self._runtime is None:
            self._mentor_title_provider: GenerateMentorTitleProvider = (
                UnavailableGenerateMentorTitleProvider()
            )
        else:
            from shifu.intelligence.providers.mentor_title.agentos import (
                AgentOSMentorTitleProvider,
            )

            self._mentor_title_provider = AgentOSMentorTitleProvider(
                self._runtime.client, self._handoffs
            )
        self._closed = False

    @property
    def client(self) -> AgentOSClient:
        if self._runtime is None:
            raise ServiceUnavailableError('AGENTOS_DATABASE_URL is required.')
        return self._runtime.client

    @property
    def database(self) -> IntelligenceDatabase:
        return self._database

    @property
    def code_rubric_assessor_provider(self) -> CodeRubricAssessorProvider:
        return self._code_rubric_client

    @property
    def mentor_title_provider(self) -> GenerateMentorTitleProvider:
        return self._mentor_title_provider

    @property
    def file_storage_provider(self) -> FileStorageProvider:
        return self._storage_provider

    @property
    def attachment_extractor_provider(self) -> LocalMentorAttachmentExtractorProvider:
        return self._extractor_provider

    @property
    def purge_mentor_attachments_use_case(self) -> PurgeMentorAttachmentsUseCase:
        return self._purge_mentor_attachments_use_case

    @property
    def purge_mentor_summaries_use_case(self) -> PurgeMentorSummariesForAccountUseCase:
        return self._purge_mentor_summaries_use_case

    @property
    def purge_learner_memories_use_case(self) -> PurgeLearnerMemoriesForAccountUseCase:
        return self._purge_learner_memories_use_case

    @property
    def purge_mentor_action_proposals_use_case(
        self,
    ) -> PurgeMentorActionProposalsForAccountUseCase:
        return self._purge_mentor_action_proposals_use_case

    @property
    def record_mentor_action_outcome_use_case(
        self,
    ) -> RecordMentorActionOutcomeUseCase:
        return self._record_mentor_action_outcome_use_case

    @property
    def learner_memory_analyzer_provider(self) -> LearnerMemoryAnalyzerProvider:
        return self._learner_memory_analyzer_provider

    @property
    def learner_memory_similarity_provider(self) -> LearnerMemorySimilarityProvider:
        return self._learner_memory_similarity_provider

    @property
    def summarizer_provider(self) -> MentorConversationSummarizerProvider:
        return self._summarizer_provider

    @property
    def route_provider(self) -> MentorRouteProvider:
        return self._route_provider

    @property
    def planning_intent_classifier(self) -> PlanningIntentClassifierProvider:
        return self._planning_intent_classifier

    @property
    def planning_skill_retrieval(self) -> PlanningSkillRetrievalProvider:
        return self._planning_skill_retrieval

    @property
    def observability_provider(self) -> LangfuseTelemetryProvider:
        if self._runtime is not None:
            return self._runtime.observability
        return self._observability_provider

    def destination_for_event(self, event: OutboxEvent) -> str | None:
        if event.name not in {
            _MENTOR_EVENT,
            _ATTACHMENT_PREPARE_EVENT,
            _ATTACHMENT_CLEANUP_EVENT,
        }:
            return None
        return 'agentos:intelligence'

    @staticmethod
    def _project_event(
        event: OutboxEvent,
    ) -> tuple[str, Mapping[str, str]] | None:
        payload = event.payload
        if event.name == _MENTOR_EVENT:
            attempt_id = payload.get('attempt_id')
            if isinstance(attempt_id, str) and attempt_id:
                return (
                    'intelligence-process-mentor-response',
                    {'attempt_id': attempt_id, 'event_id': event.id},
                )
            return None
        if event.name == _ATTACHMENT_PREPARE_EVENT:
            attachment_id = payload.get('attachment_id')
            generation = payload.get('generation')
            if isinstance(attachment_id, str) and type(generation) is int:
                return (
                    'intelligence-prepare-mentor-attachment',
                    {
                        'attachment_id': attachment_id,
                        'generation': str(generation),
                        'event_id': event.id,
                    },
                )
            return None
        if event.name == _ATTACHMENT_CLEANUP_EVENT:
            account_id = payload.get('account_id')
            generation = payload.get('deletion_generation')
            session_id = payload.get('session_id')
            batch_id = payload.get('batch_id')
            if (
                isinstance(account_id, str)
                and type(generation) is int
                and (session_id is None or isinstance(session_id, str))
                and (batch_id is None or isinstance(batch_id, str))
                and not (session_id is not None and batch_id is not None)
            ):
                fields = {
                    'account_id': account_id,
                    'deletion_generation': str(generation),
                }
                if session_id is not None:
                    fields['session_id'] = session_id
                if batch_id is not None:
                    fields['batch_id'] = batch_id
                return 'intelligence-purge-mentor-attachments', fields
        return None

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None]:
        if self._runtime is None:
            raise ServiceUnavailableError('AGENTOS_DATABASE_URL is required.')
        try:
            await self._runtime.start()
        except BaseException:
            await self.close()
            raise
        try:
            yield
        finally:
            await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._handoffs.clear()
        if self._runtime is not None:
            await self._runtime.close()
        self._storage_provider.close()
        self._code_rubric_http_client.close()
        if self._generation_limit_client is not None:
            self._generation_limit_client.close()

    @staticmethod
    def _build_code_rubric_client() -> httpx.Client:
        return httpx.Client()

    @staticmethod
    def _build_code_rubric_provider(
        settings: Settings, client: httpx.Client
    ) -> JevCodeRubricAssessorProvider:
        return JevCodeRubricAssessorProvider(
            api_key=settings.openrouter_api_key,
            client=client,
            decisions_url=str(settings.openrouter_decisions_url),
            model=settings.jev_model,
        )

    def _record_attachment_usage(self, usage: MentorInferenceUsage) -> None:
        try:
            self._telemetry.record_inference(
                usage.profile,
                usage.used_tokens,
                usage.input_tokens,
                usage.output_tokens,
                usage.cost_usd,
            )
        except Exception:  # noqa: BLE001 - attachment telemetry is best effort.
            return
