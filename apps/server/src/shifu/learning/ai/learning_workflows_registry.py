"""Learning-owned AgentOS composition and lifecycle boundary."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, ClassVar

from shifu.learning.ai.agno.workflows import EvaluateCodeActivityWorkflow
from shifu.learning.ai.agno.workflows.evaluate_code_activity_workflow import (
    AgentOSCodeRubricAssessorProvider,
)
from shifu.learning.core.use_cases import (
    EvaluateChoiceActivityUseCase,
    FailCodeActivityEvaluationUseCase,
    PrepareCodeActivityEvaluationUseCase,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
    CurriculumChoiceActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.messaging.agentos.agentos_runtime import AgentOSRuntime
from shifu.shared.messaging.agentos.agentos_settings import AgentOSQueueSettings
from shifu.shared.providers.system_clock_provider import SystemClockProvider

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

    from sqlalchemy.engine import Engine

    from shifu.learning.core.interfaces import LearningDatabase
    from shifu.shared.core.interfaces import (
        CodeRubricAssessorProvider,
        CurriculumContentProvider,
        MentorAccessProvider,
        OutboxEvent,
    )
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.messaging.agentos.agentos_observability import (
        AgentOSObservability,
    )
    from shifu.shared.settings import Settings


_EVENT_NAME = 'learning/activity-submission.requested'


class LearningWorkflowsRegistry:
    MODULE_ID: ClassVar[str] = 'learning'

    def __init__(
        self,
        settings: Settings,
        observability: AgentOSObservability | None,
        assessor: CodeRubricAssessorProvider,
        access_provider: MentorAccessProvider,
        curriculum_content_provider: CurriculumContentProvider,
        *,
        outbox_engine: Engine,
    ) -> None:
        database_url = settings.agentos_database_url
        self._settings = settings
        self._assessor = assessor
        self._access_provider = access_provider
        self._curriculum_content_provider = curriculum_content_provider
        self._database: LearningDatabase = LearningPipe.create_database(outbox_engine)
        self._clock_provider = SystemClockProvider()
        self._handoffs = AgentOSHandoffStore()
        prepare = PrepareCodeActivityEvaluationUseCase(
            self._database, settings.max_code_assessment_input_bytes
        )
        fail = FailCodeActivityEvaluationUseCase(self._database)
        evaluate = EvaluateChoiceActivityUseCase(
            self._database,
            self._clock_provider,
            curriculum_content_provider,
        )
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            fail,
            assessor,
            self._handoffs,
        )
        self._runtime = (
            AgentOSRuntime(
                module='learning',
                agentos_id='shifu-learning',
                schema='agentos_learning',
                database_url=str(database_url),
                redis_url=settings.redis_url,
                queue_settings=AgentOSQueueSettings.for_module('learning', settings),
                workflows=[workflow],
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
        self._closed = False

    @property
    def client(self) -> AgentOSClient:
        if self._runtime is None:
            raise ServiceUnavailableError('AGENTOS_DATABASE_URL is required.')
        return self._runtime.client

    @property
    def database(self) -> LearningDatabase:
        return self._database_port

    @property
    def code_rubric_assessor(self) -> CodeRubricAssessorProvider:
        return self._assessment_provider

    @property
    def observability(self) -> AgentOSObservability | None:
        return self._runtime.observability if self._runtime is not None else None

    def destination_for_event(self, event: OutboxEvent) -> str | None:
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
        if isinstance(snapshot, CurriculumChoiceActivitySnapshot):
            return 'inngest'
        if not isinstance(snapshot, CurriculumLearningActivitySnapshot):
            return None
        is_code = any(
            isinstance(question, CurriculumJavascriptStdinQuestionSnapshot)
            for question in snapshot.questions
        )
        return 'agentos:learning' if is_code else 'inngest'

    @staticmethod
    def _project_event(
        event: OutboxEvent,
    ) -> tuple[str, Mapping[str, str]] | None:
        if event.name != _EVENT_NAME:
            return None
        attempt_id = event.payload.get('attempt_id')
        run_id = event.payload.get('run_id')
        if not all(isinstance(value, str) and value for value in (attempt_id, run_id)):
            return None
        return (
            'learning-evaluate-code-activity',
            {'attempt_id': str(attempt_id), 'run_id': str(run_id)},
        )

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
