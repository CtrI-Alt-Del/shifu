"""Learning-owned AgentOS composition and lifecycle boundary."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, ClassVar

from shifu.learning.ai.agno.workflows import (
    EvaluateCodeActivityWorkflow,
    EvaluateTranslationActivityWorkflow,
)
from shifu.learning.ai.agno.workflows.evaluate_code_activity_workflow import (
    AgentOSCodeRubricAssessorProvider,
)
from shifu.learning.ai.agno.workflows.evaluate_translation_activity_workflow import (
    AgentOSTranslationRubricAssessorProvider,
)
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PersistActivityRubricDecisionUseCase,
    PrepareCodeActivityEvaluationUseCase,
    PrepareTranslationActivityEvaluationUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
    CurriculumChoiceActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
    TranslationRubricAssessmentInput,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.messaging.agentos.agentos_runtime import AgentOSRuntime
from shifu.shared.messaging.agentos.agentos_settings import AgentOSQueueSettings
from shifu.shared.providers.langfuse_telemetry_provider import LangfuseTelemetryProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from langfuse import Langfuse
    from sqlalchemy.engine import Engine

    from shifu.learning.core.interfaces import LearningDatabase
    from shifu.shared.core.interfaces import (
        AccountActivityProvider,
        CodeRubricAssessorProvider,
        CurriculumContentProvider,
        MentorAccessProvider,
        OutboxEvent,
        TranslationRubricAssessorProvider,
    )
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.settings import Settings


_EVENT_NAME = 'learning/activity-submission.requested'


class LearningWorkflowsRegistry:
    MODULE_ID: ClassVar[str] = 'learning'

    def __init__(
        self,
        settings: Settings,
        observability: LangfuseTelemetryProvider | None,
        assessor: CodeRubricAssessorProvider,
        translation_assessor: TranslationRubricAssessorProvider,
        access_provider: MentorAccessProvider,
        curriculum_content_provider: CurriculumContentProvider,
        *,
        outbox_engine: Engine,
        account_activity_provider: AccountActivityProvider,
        telemetry_client: Langfuse | None = None,
        telemetry_provider: TelemetryProvider | None = None,
    ) -> None:
        database_url = settings.agentos_database_url
        observability = observability or LangfuseTelemetryProvider(
            'learning', telemetry_client
        )
        self._observability_provider: LangfuseTelemetryProvider = observability
        self._settings = settings
        self._assessor = assessor
        self._translation_assessor = translation_assessor
        self._access_provider = access_provider
        self._account_activity_provider = account_activity_provider
        self._curriculum_content_provider = curriculum_content_provider
        self._database: LearningDatabase = LearningPipe.create_database(outbox_engine)
        self._clock_provider = SystemClockProvider()
        self._handoffs = AgentOSHandoffStore()
        prepare = PrepareCodeActivityEvaluationUseCase(
            self._database, settings.max_code_assessment_input_bytes
        )
        fail = FailCodeActivityEvaluationUseCase(self._database)
        persist_decision = PersistActivityRubricDecisionUseCase(self._database)
        evaluate = EvaluateChoiceActivityUseCase(
            self._database,
            self._clock_provider,
            curriculum_content_provider,
            max_code_assessment_input_bytes=settings.max_code_assessment_input_bytes,
        )
        prepare_translation = PrepareTranslationActivityEvaluationUseCase(
            self._database
        )
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            fail,
            persist_decision,
            assessor,
            self._handoffs,
            account_activity_provider,
            self._attempt_account_id,
            observability,
            telemetry_provider,
        )
        translation_workflow = EvaluateTranslationActivityWorkflow(
            prepare_translation,
            evaluate,
            fail,
            persist_decision,
            translation_assessor,
            self._handoffs,
            account_activity_provider,
            self._attempt_account_id,
            observability,
        )
        self._runtime = (
            AgentOSRuntime(
                module='learning',
                agentos_id='shifu-learning',
                schema='agentos_learning',
                database_url=str(database_url),
                redis_url=settings.redis_url,
                queue_settings=AgentOSQueueSettings.for_module('learning', settings),
                workflows=[workflow, translation_workflow],
                workflow_event_projector=self._project_event,
                outbox_engine=outbox_engine,
                observability=observability,
            )
            if database_url is not None
            else None
        )
        self._database_port: LearningDatabase = self._database
        self._assessment_provider: CodeRubricAssessorProvider = (
            AgentOSCodeRubricAssessorProvider(self._runtime.client, self._handoffs)
            if self._runtime is not None
            else _UnavailableCodeRubricAssessorProvider()
        )
        self._translation_assessment_provider: TranslationRubricAssessorProvider = (
            AgentOSTranslationRubricAssessorProvider(
                self._runtime.client, self._handoffs
            )
            if self._runtime is not None
            else _UnavailableTranslationRubricAssessorProvider()
        )
        self._closed = False

    @property
    def client(self) -> AgentOSClient:
        if self._runtime is None:
            raise ServiceUnavailableError('AGENTOS_DATABASE_URL is required.')
        return self._runtime.client

    @property
    def database(self) -> LearningDatabase:
        return self._database_port

    def _attempt_account_id(self, attempt_id: str) -> str | None:
        """Resolve the persisted Learning owner before the account gate is entered."""
        with self._database.transaction() as repositories:
            return repositories.activity_attempts.find_account_id_by_attempt_id(
                attempt_id
            )

    @property
    def code_rubric_assessor_provider(self) -> CodeRubricAssessorProvider:
        return self._assessment_provider

    @property
    def translation_rubric_assessor_provider(self) -> TranslationRubricAssessorProvider:
        return self._translation_assessment_provider

    @property
    def observability_provider(self) -> LangfuseTelemetryProvider:
        return self._observability_provider

    def destination_for_event(self, event: OutboxEvent) -> str | None:
        snapshot = self._event_snapshot(event)
        if snapshot is None:
            return None
        if isinstance(snapshot, CurriculumChoiceActivitySnapshot):
            return 'inngest'
        is_ai_graded = any(
            isinstance(
                question,
                (
                    CurriculumJavascriptStdinQuestionSnapshot,
                    CurriculumReactQuestionSnapshot,
                    CurriculumHtmlCssJsQuestionSnapshot,
                    CurriculumReactFastifyQuestionSnapshot,
                    CurriculumTranslationQuestionSnapshot,
                ),
            )
            for question in snapshot.questions
        )
        return 'agentos:learning' if is_ai_graded else 'inngest'

    def _project_event(
        self,
        event: OutboxEvent,
    ) -> tuple[str, Mapping[str, str]] | None:
        attempt_id = event.payload.get('attempt_id')
        run_id = event.payload.get('run_id')
        if not all(isinstance(value, str) and value for value in (attempt_id, run_id)):
            return None
        snapshot = self._event_snapshot(event)
        if snapshot is None:
            return None
        is_translation = isinstance(
            snapshot, CurriculumLearningActivitySnapshot
        ) and any(
            isinstance(question, CurriculumTranslationQuestionSnapshot)
            for question in snapshot.questions
        )
        workflow_id = (
            'learning-evaluate-translation-activity'
            if is_translation
            else 'learning-evaluate-code-activity'
        )
        return (
            workflow_id,
            {'attempt_id': str(attempt_id), 'run_id': str(run_id)},
        )

    def _event_snapshot(
        self, event: OutboxEvent
    ) -> CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot | None:
        if event.name != _EVENT_NAME:
            return None
        attempt_id = event.payload.get('attempt_id')
        if not isinstance(attempt_id, str) or not attempt_id:
            return None
        with self._database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
        if attempt is None:
            return None
        snapshot = attempt.grading_snapshot
        if not isinstance(
            snapshot,
            (CurriculumChoiceActivitySnapshot, CurriculumLearningActivitySnapshot),
        ):
            return None
        return snapshot

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


class _UnavailableCodeRubricAssessorProvider:
    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
        del request
        raise ServiceUnavailableError('Code assessment is unavailable.')


class _UnavailableTranslationRubricAssessorProvider:
    def assess(self, request: TranslationRubricAssessmentInput) -> CodeRubricDecisions:
        del request
        raise ServiceUnavailableError('Translation assessment is unavailable.')
