"""Intelligence-owned workflow registrations and AgentOS lifecycle."""

from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, cast

import httpx

from shifu.intelligence.ai.agno.agents import (
    MentorAttachmentAnswerAgent,
    MentorAttachmentVisionAgent,
    MentorReviewerAgent,
    MentorTitleAgent,
    MentorWriterAgent,
)
from shifu.intelligence.ai.agno.workflows import (
    AgnoGenerateMentorTitleWorkflow,
    PrepareMentorAttachmentWorkflow,
    ProcessMentorResponseWorkflow,
    PurgeMentorAttachmentsWorkflow,
)
from shifu.intelligence.core.use_cases import (
    AssertMentorResponseCurrentUseCase,
    CompleteMentorAttachmentUseCase,
    FailMentorAttachmentUseCase,
    FailMentorResponseUseCase,
    PrepareMentorAttachmentUseCase,
    PrepareMentorResponseUseCase,
    PublishMentorResponseBlockUseCase,
    PurgeMentorAttachmentsUseCase,
    PurgeMentorSummariesForAccountUseCase,
    RecordMentorInferenceUsageUseCase,
    RecordMentorResponseProgressUseCase,
    ReleaseMentorAttachmentClaimUseCase,
    ReleaseMentorResponseClaimUseCase,
    RenewMentorAttachmentClaimUseCase,
    RenewMentorResponseClaimUseCase,
    SummarizeMentorSessionContextUseCase,
)
from shifu.intelligence.core.use_cases.finalize_mentor_response_use_case import (
    FinalizeMentorResponseUseCase,
)
from shifu.intelligence.core.use_cases.get_mentor_attachment_context_use_case import (
    GetMentorAttachmentContextUseCase,
)
from shifu.intelligence.pipes import IntelligencePipe
from shifu.intelligence.providers.code_rubric_assessor_provider.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.intelligence.providers.mentor_attachment.local_mentor_attachment_extractor_provider import (
    LocalMentorAttachmentExtractorProvider,
)
from shifu.intelligence.providers.openrouter import (
    MentorTitleModelProvider,
    UnavailableGenerateMentorTitleWorkflow,
)
from shifu.intelligence.providers.openrouter.mentor_answer_model_provider import (
    OpenrouterMentorAnswerModelProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.intelligence.providers.routing.lazy_mentor_route_provider import (
    LazyMentorRouteProvider,
)
from shifu.intelligence.providers.summarization.textrank.textrank_mentor_conversation_summarizer_provider import (
    TextrankMentorConversationSummarizerProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
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

    from shifu.intelligence.core.domain.structures import MentorInferenceUsage
    from shifu.intelligence.core.interfaces import (
        GenerateMentorTitleWorkflow,
        IntelligenceDatabase,
        MentorConversationSummarizerProvider,
        MentorEmbeddingsProvider,
        MentorRouteProvider,
        MentorTelemetryProvider,
    )
    from shifu.shared.core.interfaces import (
        CodeRubricAssessorProvider,
        FileStorageProvider,
        MentorAccessProvider,
        MentorCatalogProvider,
        MentorContextProvider,
        OutboxEvent,
    )
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
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


class _UnavailableAttachmentAnswerAgent:
    def answer(self, *_args: object, **_kwargs: object) -> object:
        raise ServiceUnavailableError('Mentor attachment answers are unavailable.')


class _UnavailableReviewerAgent:
    def review(self, *_args: object, **_kwargs: object) -> object:
        raise ServiceUnavailableError('Mentor response review is unavailable.')


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
        *,
        outbox_engine: Engine,
        telemetry_client: Langfuse | None = None,
        route_provider: MentorRouteProvider | None = None,
        telemetry: MentorTelemetryProvider | None = None,
        telemetry_provider: TelemetryProvider | None = None,
        summarizer: MentorConversationSummarizerProvider | None = None,
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
        self._summarizer: MentorConversationSummarizerProvider = (
            summarizer
            if summarizer is not None
            else TextrankMentorConversationSummarizerProvider(
                self._shared_preprocessor, self._shared_embeddings
            )
        )
        self._handoffs = AgentOSHandoffStore()
        self._storage_provider = FileStoragePipe.create_file_storage_provider(settings)
        self._extractor_provider = LocalMentorAttachmentExtractorProvider(
            settings, self._identifier_provider
        )

        title_model = MentorTitleModelProvider.build(
            settings,
            telemetry_provider=telemetry_provider,
        )
        title_agent = (
            MentorTitleAgent(title_model)
            if title_model is not None
            else cast('MentorTitleAgent', _UnavailableTitleAgent())
        )
        title_workflow = AgnoGenerateMentorTitleWorkflow(
            title_agent, self._handoffs, observability
        )

        vision_model = OpenrouterMentorAnswerModelProvider.build(
            settings,
            profile='vision',
            telemetry_provider=telemetry_provider,
        )
        vision_agent = (
            MentorAttachmentVisionAgent(vision_model)
            if vision_model is not None
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
        prepare_workflow = PrepareMentorAttachmentWorkflow(
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
        purge_workflow = PurgeMentorAttachmentsWorkflow(
            self._purge_mentor_attachments_use_case
        )

        attachment_context_use_case = GetMentorAttachmentContextUseCase(
            self._database,
            self._identifier_provider,
            access_provider,
        )
        prepare_response = PrepareMentorResponseUseCase(
            self._database,
            self._clock_provider,
            access_provider,
            context_provider,
            self._route_provider,
            catalog_provider,
            attachment_context_use_case,
        )
        publish_response_block = PublishMentorResponseBlockUseCase(
            self._database, self._clock_provider, access_provider, context_provider
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
            self._summarizer,
            access_provider,
            self._clock_provider,
            self._identifier_provider,
            record_response_progress,
            renew_response_claim,
            self._telemetry,
        )
        self._purge_mentor_summaries_use_case = PurgeMentorSummariesForAccountUseCase(
            self._database
        )
        writer_model = OpenrouterMentorAnswerModelProvider.build(
            settings,
            profile='primary',
            telemetry_provider=telemetry_provider,
        )
        attachment_answer_model = OpenrouterMentorAnswerModelProvider.build(
            settings,
            profile='primary',
            telemetry_provider=telemetry_provider,
        )
        reviewer_model = OpenrouterMentorAnswerModelProvider.build(
            settings,
            profile='reviewer',
            telemetry_provider=telemetry_provider,
        )
        writer_agent = (
            MentorWriterAgent(writer_model)
            if writer_model is not None
            else cast('MentorWriterAgent', _UnavailableWriterAgent())
        )
        attachment_answer_agent = (
            MentorAttachmentAnswerAgent(attachment_answer_model)
            if attachment_answer_model is not None
            else cast(
                'MentorAttachmentAnswerAgent', _UnavailableAttachmentAnswerAgent()
            )
        )
        reviewer_agent = (
            MentorReviewerAgent(reviewer_model)
            if reviewer_model is not None
            else cast('MentorReviewerAgent', _UnavailableReviewerAgent())
        )
        process_workflow = ProcessMentorResponseWorkflow(
            summarize_use_case=summarize_context,
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
            settings,
            self._code_rubric_http_client,
            telemetry_provider,
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
        self._observability = (
            self._runtime.observability if self._runtime is not None else observability
        )
        if isinstance(self._telemetry, LangfuseMentorTelemetryProvider):
            self._telemetry.bind(self._observability)
        if self._runtime is None:
            self._mentor_title_provider: GenerateMentorTitleWorkflow = (
                UnavailableGenerateMentorTitleWorkflow()
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
    def code_rubric_assessor(self) -> CodeRubricAssessorProvider:
        return self._code_rubric_client

    @property
    def mentor_title_provider(self) -> GenerateMentorTitleWorkflow:
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
    def summarizer(self) -> MentorConversationSummarizerProvider:
        return self._summarizer

    @property
    def route_provider(self) -> MentorRouteProvider:
        return self._route_provider

    @property
    def observability(self) -> LangfuseTelemetryProvider:
        if self._runtime is not None:
            return self._runtime.observability
        return self._observability

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

    @staticmethod
    def _build_code_rubric_client() -> httpx.Client:
        return httpx.Client()

    @staticmethod
    def _build_code_rubric_provider(
        settings: Settings,
        client: httpx.Client,
        telemetry_provider: TelemetryProvider | None,
    ) -> JevCodeRubricAssessorProvider:
        return JevCodeRubricAssessorProvider(
            api_key=settings.openrouter_api_key,
            client=client,
            decisions_url=str(settings.openrouter_decisions_url),
            model=settings.jev_model,
            telemetry_provider=telemetry_provider,
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
