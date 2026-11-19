"""One Learning workflow for durable grading and transient translation handoff."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import ValidationError

from shifu.learning.ai.agno.workflows.agentos_assessment_support import (
    HandoffAssessmentInput,
    OfficialRunInput,
    complete_unavailable,
    execution_for_step,
    safe_native_input,
)
from shifu.learning.core.domain.structures import (
    TranslationQuestionAssessmentDecisions,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricDecisions,
    TranslationRubricAssessmentInput,
)

if TYPE_CHECKING:
    from agno.run.workflow import WorkflowRunOutput

    from shifu.learning.core.domain.structures import (
        PreparedTranslationActivityEvaluation,
    )
    from shifu.learning.core.use_cases import (
        EvaluateChoiceActivityUseCase,
        FailCodeActivityEvaluationUseCase,
        PrepareTranslationActivityEvaluationUseCase,
    )
    from shifu.shared.providers.langfuse_telemetry_provider import (
        LangfuseTelemetryProvider,
    )
    from shifu.shared.core.interfaces import TranslationRubricAssessorProvider
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )


_HANDOFF_CAPABILITY = 'learning-translation-assessment'
_UNAVAILABLE = 'Translation assessment is unavailable.'


@dataclass(slots=True)
class _Execution:
    raw_input: object
    official: OfficialRunInput | None = None
    handoff_ref: str | None = None
    prepared: PreparedTranslationActivityEvaluation | None = None
    assessment: TranslationRubricAssessmentInput | None = None
    decisions: tuple[TranslationQuestionAssessmentDecisions, ...] = ()
    failure: bool = False


class EvaluateTranslationActivityWorkflow(Workflow):
    """Run the translation rubric assessor inside its visible native workflow graph."""

    def __init__(
        self,
        prepare_use_case: PrepareTranslationActivityEvaluationUseCase,
        evaluate_use_case: EvaluateChoiceActivityUseCase,
        fail_use_case: FailCodeActivityEvaluationUseCase,
        assessor: TranslationRubricAssessorProvider,
        handoffs: AgentOSHandoffStore,
        observability: LangfuseTelemetryProvider | None = None,
    ) -> None:
        self._prepare_use_case = prepare_use_case
        self._evaluate_use_case = evaluate_use_case
        self._fail_use_case = fail_use_case
        self._assessor = assessor
        self._observability: LangfuseTelemetryProvider | None = observability
        self._handoffs = handoffs
        self._execution: ContextVar[_Execution | None] = ContextVar(
            'learning_translation_activity_execution', default=None
        )
        super().__init__(
            id='learning-evaluate-translation-activity',
            name='Evaluate Translation Activity',
            steps=[
                Step(
                    name='prepare-frozen-assessment',
                    executor=self._prepare_translation,
                    max_retries=0,
                ),
                Step(
                    name='assess-translation-rubrics',
                    executor=self._assess_translation,
                    max_retries=0,
                ),
                Step(
                    name='apply-or-handoff-decisions',
                    executor=self._apply_translation,
                    max_retries=0,
                ),
            ],
            telemetry=False,
            store_events=False,
            store_media=False,
            store_executor_outputs=False,
            cache_session=False,
        )

    def deep_copy(
        self, *, update: dict[str, object] | None = None
    ) -> EvaluateTranslationActivityWorkflow:
        workflow = EvaluateTranslationActivityWorkflow(
            self._prepare_use_case,
            self._evaluate_use_case,
            self._fail_use_case,
            self._assessor,
            self._handoffs,
            self._observability,
        )
        workflow.db = self.db
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    def run(  # pyright: ignore[reportIncompatibleMethodOverride] - native transport accepts strict event envelopes.
        self, input: object
    ) -> WorkflowRunOutput:
        execution = _Execution(raw_input=input)
        token = self._execution.set(execution)
        try:
            return super().run(input=safe_native_input(input, _UNAVAILABLE))
        finally:
            self._execution.reset(token)

    def _execution_for_step(self, step_input: StepInput) -> _Execution:
        return execution_for_step(
            self._execution, step_input, lambda raw: _Execution(raw_input=raw)
        )

    def _prepare_translation(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            official = OfficialRunInput.model_validate_json(
                safe_native_input(execution.raw_input, _UNAVAILABLE), strict=True
            )
        except (ServiceUnavailableError, ValidationError):
            official = None
        if official is not None:
            execution.official = official
            try:
                execution.prepared = self._prepare_use_case.execute(
                    official.attempt_id, official.run_id
                )
            except Exception:  # noqa: BLE001 - Core failures stay private to the run.
                execution.failure = True
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            return StepOutput(
                content='prepared' if execution.prepared is not None else 'stale'
            )

        try:
            request = HandoffAssessmentInput.model_validate_json(
                safe_native_input(execution.raw_input, _UNAVAILABLE), strict=True
            )
            source = self._handoffs.read_input(
                request.handoff_ref, capability=_HANDOFF_CAPABILITY
            )
            if not isinstance(source, TranslationRubricAssessmentInput):
                execution.failure = True
                return StepOutput(content='unavailable')
            execution.handoff_ref = request.handoff_ref
            execution.assessment = source
        except Exception:  # noqa: BLE001 - keep private transport details out of AgentOS.
            execution.failure = True
            raise ServiceUnavailableError(_UNAVAILABLE) from None
        return StepOutput(content='prepared')

    def _assess_translation(self, step_input: StepInput) -> StepOutput:
        started = perf_counter()
        execution = self._execution_for_step(step_input)
        try:
            return self._assess_execution(step_input)
        finally:
            if self._observability is not None:
                self._observability.record(
                    stage='evaluate',
                    outcome='failed' if execution.failure else 'passed',
                    duration_ms=(perf_counter() - started) * 1000,
                    correlation_id=uuid4().hex,
                    model_profile='translation-rubric',
                    counts={'inference_requests': len(execution.decisions)},
                )

    def _assess_execution(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        if execution.failure:
            return StepOutput(content='skipped')
        try:
            if execution.official is not None:
                prepared = execution.prepared
                if prepared is None:
                    return StepOutput(content='skipped')
                execution.decisions = tuple(
                    TranslationQuestionAssessmentDecisions(
                        question_key=item.question_key,
                        decisions=self._assessor.assess(item.assessment_input),
                    )
                    for item in prepared.questions
                )
            elif execution.assessment is not None:
                if execution.handoff_ref is None:
                    execution.failure = True
                    return StepOutput(content='unavailable')
                decisions = self._assessor.assess(execution.assessment)
                self._handoffs.complete(
                    execution.handoff_ref,
                    capability=_HANDOFF_CAPABILITY,
                    result_value=decisions,
                )
                execution.decisions = (
                    TranslationQuestionAssessmentDecisions(
                        question_key='', decisions=decisions
                    ),
                )
            else:
                execution.failure = True
                return StepOutput(content='unavailable')
        except Exception:  # noqa: BLE001 - provider content never enters run state.
            execution.failure = True
            if execution.handoff_ref is not None:
                complete_unavailable(
                    self._handoffs, execution.handoff_ref, _HANDOFF_CAPABILITY
                )
            if execution.official is not None:
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            return StepOutput(content='unavailable')
        return StepOutput(content='assessed')

    def _apply_translation(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            return self._apply_execution(execution)
        finally:
            self._execution.set(None)

    def _apply_execution(self, execution: _Execution) -> StepOutput:
        if execution.official is not None:
            prepared = execution.prepared
            if prepared is None:
                return StepOutput(content='stale')
            if execution.failure:
                try:
                    self._fail_use_case.execute(prepared.attempt_id, prepared.run_id)
                except Exception:  # noqa: BLE001 - persist only safe failure state.
                    raise ServiceUnavailableError(_UNAVAILABLE) from None
                return StepOutput(content='failed')
            try:
                committed = self._evaluate_use_case.execute(
                    prepared.attempt_id,
                    prepared.run_id,
                    translation_decisions=execution.decisions,
                )
            except Exception:  # noqa: BLE001 - only a safe class crosses the run boundary.
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            if not committed:
                return StepOutput(content='stale')
            return StepOutput(content='completed')
        if execution.failure:
            return StepOutput(content='unavailable')
        return StepOutput(content='complete')


class AgentOSTranslationRubricAssessorProvider:
    """Shared assessor adapter for the existing synchronous preview use case."""

    def __init__(self, client: AgentOSClient, handoffs: AgentOSHandoffStore) -> None:
        self._client = client
        self._handoffs = handoffs

    def assess(self, request: TranslationRubricAssessmentInput) -> CodeRubricDecisions:
        reference = self._handoffs.create(
            capability=_HANDOFF_CAPABILITY,
            input_value=request,
        )
        try:
            self._client.submit_workflow(
                workflow_id='learning-evaluate-translation-activity',
                fields={'handoff_ref': reference},
                background=False,
                session_id=f'assessment-{reference}',
                timeout_seconds=65.0,
            )
            result = self._handoffs.take_result(
                reference,
                capability=_HANDOFF_CAPABILITY,
            )
        except Exception as error:
            self._handoffs.discard(reference)
            raise ServiceUnavailableError(_UNAVAILABLE) from error
        if isinstance(result, CodeRubricDecisions):
            return result
        raise ServiceUnavailableError(_UNAVAILABLE)
