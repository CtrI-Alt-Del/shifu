"""One Learning workflow for durable grading and transient assessment handoff."""

from __future__ import annotations

import json
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.learning.core.domain.structures import (
    CodeQuestionAssessmentDecisions,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
)

if TYPE_CHECKING:
    from agno.run.workflow import WorkflowRunOutput

    from shifu.learning.core.domain.structures import PreparedCodeActivityEvaluation
    from shifu.learning.core.use_cases import (
        EvaluateChoiceActivityUseCase,
        FailCodeActivityEvaluationUseCase,
        PrepareCodeActivityEvaluationUseCase,
    )
    from shifu.shared.core.interfaces import CodeRubricAssessorProvider
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )


_HANDOFF_CAPABILITY = 'learning-code-assessment'
_UNAVAILABLE = 'Code assessment is unavailable.'


class _OfficialInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    attempt_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)


class _AssessmentInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    handoff_ref: str = Field(min_length=20, max_length=128)


@dataclass(slots=True)
class _Execution:
    raw_input: object
    official: _OfficialInput | None = None
    handoff_ref: str | None = None
    prepared: PreparedCodeActivityEvaluation | None = None
    assessment: CodeRubricAssessmentInput | None = None
    decisions: tuple[CodeQuestionAssessmentDecisions, ...] = ()
    failure: bool = False


class EvaluateCodeActivityWorkflow(Workflow):
    """Run the Jev provider directly inside its visible native workflow graph."""

    def __init__(
        self,
        prepare_use_case: PrepareCodeActivityEvaluationUseCase,
        evaluate_use_case: EvaluateChoiceActivityUseCase,
        fail_use_case: FailCodeActivityEvaluationUseCase,
        assessor: CodeRubricAssessorProvider,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        self._prepare_use_case = prepare_use_case
        self._evaluate_use_case = evaluate_use_case
        self._fail_use_case = fail_use_case
        self._assessor = assessor
        self._handoffs = handoffs
        self._execution: ContextVar[_Execution | None] = ContextVar(
            'learning_code_activity_execution', default=None
        )
        super().__init__(
            id='learning-evaluate-code-activity',
            name='Evaluate Code Activity',
            steps=[
                Step(
                    name='prepare-frozen-assessment',
                    executor=self._prepare,
                    max_retries=0,
                ),
                Step(name='assess-code-rubrics', executor=self._assess, max_retries=0),
                Step(
                    name='apply-or-handoff-decisions',
                    executor=self._apply,
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
    ) -> EvaluateCodeActivityWorkflow:
        workflow = EvaluateCodeActivityWorkflow(
            self._prepare_use_case,
            self._evaluate_use_case,
            self._fail_use_case,
            self._assessor,
            self._handoffs,
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
            return super().run(input=self._safe_native_input(input))
        finally:
            self._execution.reset(token)

    @staticmethod
    def _safe_native_input(raw: object) -> str:
        if isinstance(raw, str):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                raise ServiceUnavailableError(_UNAVAILABLE) from None
        else:
            value = raw
        try:
            official = _OfficialInput.model_validate(value, strict=True)
            return official.model_dump_json()
        except ValidationError:
            try:
                assessment = _AssessmentInput.model_validate(value, strict=True)
                return assessment.model_dump_json()
            except ValidationError:
                raise ServiceUnavailableError(_UNAVAILABLE) from None

    def _execution_for_step(self, step_input: StepInput) -> _Execution:
        execution = self._execution.get()
        if execution is None:
            execution = _Execution(raw_input=step_input.input)
            self._execution.set(execution)
        return execution

    def _prepare(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            official = _OfficialInput.model_validate_json(
                self._safe_native_input(execution.raw_input), strict=True
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
            request = _AssessmentInput.model_validate_json(
                self._safe_native_input(execution.raw_input), strict=True
            )
            source = self._handoffs.read_input(
                request.handoff_ref, capability=_HANDOFF_CAPABILITY
            )
            if not isinstance(source, CodeRubricAssessmentInput):
                execution.failure = True
                return StepOutput(content='unavailable')
            execution.handoff_ref = request.handoff_ref
            execution.assessment = source
        except Exception:  # noqa: BLE001 - keep private transport details out of AgentOS.
            execution.failure = True
            raise ServiceUnavailableError(_UNAVAILABLE) from None
        return StepOutput(content='prepared')

    def _assess(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        if execution.failure:
            return StepOutput(content='skipped')
        try:
            if execution.official is not None:
                prepared = execution.prepared
                if prepared is None:
                    return StepOutput(content='skipped')
                execution.decisions = tuple(
                    CodeQuestionAssessmentDecisions(
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
                    CodeQuestionAssessmentDecisions(
                        question_key='', decisions=decisions
                    ),
                )
            else:
                execution.failure = True
                return StepOutput(content='unavailable')
        except Exception:  # noqa: BLE001 - Jev content never enters run state.
            execution.failure = True
            if execution.handoff_ref is not None:
                self._complete_unavailable(execution.handoff_ref)
            if execution.official is not None:
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            return StepOutput(content='unavailable')
        return StepOutput(content='assessed')

    def _apply(self, step_input: StepInput) -> StepOutput:
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
                self._evaluate_use_case.execute(
                    prepared.attempt_id,
                    prepared.run_id,
                    execution.decisions,
                )
            except Exception:  # noqa: BLE001 - only a safe class crosses the run boundary.
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            return StepOutput(content='completed')
        if execution.failure:
            return StepOutput(content='unavailable')
        return StepOutput(content='complete')

    def _complete_unavailable(self, reference: str) -> None:
        try:
            self._handoffs.complete(
                reference,
                capability=_HANDOFF_CAPABILITY,
                result_value='unavailable',
            )
        except KeyError:
            return


class AgentOSCodeRubricAssessorProvider:
    """Shared assessor adapter for the existing synchronous preview use case."""

    def __init__(self, client: AgentOSClient, handoffs: AgentOSHandoffStore) -> None:
        self._client = client
        self._handoffs = handoffs

    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
        reference = self._handoffs.create(
            capability=_HANDOFF_CAPABILITY,
            input_value=request,
        )
        try:
            self._client.submit_workflow(
                workflow_id='learning-evaluate-code-activity',
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
