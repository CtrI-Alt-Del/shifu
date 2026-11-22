"""Durable Learning workflow that assesses practical preparation photos.

Photos are read from Learning's private storage by object key inside the assess
step. They never enter AgentOS state, step outputs, logs or telemetry: only
short status strings cross the step boundaries.
"""

from __future__ import annotations

import logging
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
    OfficialRunInput,
    execution_for_step,
    safe_native_input,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    PracticePhotoAssessmentInput,
    PracticePhotoAssessmentPhoto,
    PracticePhotoDecisions,
)

if TYPE_CHECKING:
    from agno.run.workflow import WorkflowRunOutput

    from shifu.learning.core.domain.structures import (
        PreparedPracticalPreparationEvaluation,
    )
    from shifu.learning.core.use_cases import (
        EvaluateChoiceActivityUseCase,
        FailCodeActivityEvaluationUseCase,
        PreparePracticalPreparationActivityEvaluationUseCase,
    )
    from shifu.shared.core.interfaces import (
        FileStorageProvider,
        PracticePhotoAssessorProvider,
    )
    from shifu.shared.providers.langfuse_telemetry_provider import (
        LangfuseTelemetryProvider,
    )


_logger = logging.getLogger(__name__)
_UNAVAILABLE = 'Practical preparation assessment is unavailable.'
WORKFLOW_ID = 'learning-evaluate-practical-preparation-activity'


@dataclass(slots=True)
class _Execution:
    raw_input: object
    official: OfficialRunInput | None = None
    prepared: PreparedPracticalPreparationEvaluation | None = None
    decisions: PracticePhotoDecisions | None = None
    failure: bool = False
    stage: str | None = None
    error_class: str | None = None


class EvaluatePracticalPreparationActivityWorkflow(Workflow):
    """Read the photos, call the assessor port and let Core grade or close the attempt."""

    def __init__(
        self,
        prepare_use_case: PreparePracticalPreparationActivityEvaluationUseCase,
        evaluate_use_case: EvaluateChoiceActivityUseCase,
        fail_use_case: FailCodeActivityEvaluationUseCase,
        assessor: PracticePhotoAssessorProvider,
        storage: FileStorageProvider,
        observability: LangfuseTelemetryProvider | None = None,
    ) -> None:
        self._prepare_use_case = prepare_use_case
        self._evaluate_use_case = evaluate_use_case
        self._fail_use_case = fail_use_case
        self._assessor = assessor
        self._storage = storage
        self._observability: LangfuseTelemetryProvider | None = observability
        self._execution: ContextVar[_Execution | None] = ContextVar(
            'learning_practical_preparation_execution', default=None
        )
        super().__init__(
            id=WORKFLOW_ID,
            name='Evaluate Practical Preparation Activity',
            steps=[
                Step(
                    name='prepare-practical-preparation',
                    executor=self._prepare_practical,
                    max_retries=0,
                ),
                Step(
                    name='assess-practice-photos',
                    executor=self._assess_practical,
                    max_retries=0,
                ),
                Step(
                    name='apply-practical-decisions',
                    executor=self._apply_practical,
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
    ) -> EvaluatePracticalPreparationActivityWorkflow:
        workflow = EvaluatePracticalPreparationActivityWorkflow(
            self._prepare_use_case,
            self._evaluate_use_case,
            self._fail_use_case,
            self._assessor,
            self._storage,
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

    def _prepare_practical(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            execution.official = OfficialRunInput.model_validate_json(
                safe_native_input(execution.raw_input, _UNAVAILABLE), strict=True
            )
        except (ServiceUnavailableError, ValidationError):
            raise ServiceUnavailableError(_UNAVAILABLE) from None

        try:
            execution.prepared = self._prepare_use_case.execute(
                execution.official.attempt_id, execution.official.run_id
            )
        except Exception as error:  # noqa: BLE001 - Core failures stay private to the run.
            self._mark_failure(execution, 'prepare', error)
            return StepOutput(content='failed')
        return StepOutput(
            content='prepared' if execution.prepared is not None else 'stale'
        )

    @staticmethod
    def _mark_failure(execution: _Execution, stage: str, error: Exception) -> None:
        """Keep only the stage and the exception class: never messages, bytes or prompts."""
        execution.failure = True
        execution.stage = stage
        chain: list[str] = []
        current: BaseException | None = error
        while current is not None and len(chain) < 4:
            chain.append(type(current).__name__)
            current = current.__cause__
        execution.error_class = '<-'.join(chain)

    def _assess_practical(self, step_input: StepInput) -> StepOutput:
        started = perf_counter()
        execution = self._execution_for_step(step_input)
        try:
            return self._assess_execution(execution)
        finally:
            if self._observability is not None:
                self._observability.record(
                    stage='evaluate',
                    outcome='failed' if execution.failure else 'passed',
                    duration_ms=(perf_counter() - started) * 1000,
                    correlation_id=uuid4().hex,
                    model_profile='practice-photo-assessment',
                    counts={'inference_requests': 1},
                )

    def _assess_execution(self, execution: _Execution) -> StepOutput:
        prepared = execution.prepared
        if execution.failure or prepared is None:
            return StepOutput(content='skipped')

        try:
            execution.decisions = self._assessor.assess(
                PracticePhotoAssessmentInput(
                    prompt=prepared.question.prompt,
                    records=prepared.question.records,
                    criteria=prepared.question.criteria,
                    photos=tuple(
                        PracticePhotoAssessmentPhoto(
                            record_key=photo.record_key,
                            media_type=photo.media_type,
                            content=self._storage.read(photo.object_key),
                        )
                        for photo in prepared.photos
                    ),
                )
            )
        except Exception as error:  # noqa: BLE001 - provider and storage content never enter run state.
            self._mark_failure(execution, 'assess', error)
            return StepOutput(content='failed')
        return StepOutput(content='assessed')

    def _apply_practical(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            return self._apply_execution(execution)
        finally:
            self._execution.set(None)

    def _apply_execution(self, execution: _Execution) -> StepOutput:
        official = execution.official
        if official is None:
            raise ServiceUnavailableError(_UNAVAILABLE)

        prepared = execution.prepared
        if prepared is None and not execution.failure:
            return StepOutput(content='stale')

        if not execution.failure and execution.decisions is not None:
            try:
                committed = self._evaluate_use_case.execute(
                    official.attempt_id,
                    official.run_id,
                    practical_decisions=execution.decisions,
                )
            except Exception as error:  # noqa: BLE001 - invalid decisions are a recoverable failure.
                self._mark_failure(execution, 'apply', error)
            else:
                return StepOutput(content='evaluated' if committed else 'stale')

        # Technical failure, invalid result or uncertainty that does not prove
        # insufficiency: keep the same attempt recoverable. Never close without grade.
        _logger.warning(
            'Practical preparation evaluation failed: stage=%s error_class=%s '
            'failure_code=evaluation_failed',
            execution.stage or 'unknown',
            execution.error_class or 'unknown',
        )
        try:
            self._fail_use_case.execute(official.attempt_id, official.run_id)
        except Exception:  # noqa: BLE001 - persist only safe failure state.
            raise ServiceUnavailableError(_UNAVAILABLE) from None
        return StepOutput(content='failed')
