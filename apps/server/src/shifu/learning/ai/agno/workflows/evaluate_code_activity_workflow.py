"""One Learning workflow for durable grading and transient assessment handoff."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid4, uuid5

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
    CodeQuestionAssessmentDecisions,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from agno.run.workflow import WorkflowRunOutput

    from shifu.learning.core.domain.structures import PreparedCodeActivityEvaluation
    from shifu.learning.core.use_cases import (
        EvaluateChoiceActivityUseCase,
        FailCodeActivityEvaluationUseCase,
        PersistActivityRubricDecisionUseCase,
        PrepareCodeActivityEvaluationUseCase,
    )
    from shifu.shared.providers.langfuse_telemetry_provider import (
        LangfuseTelemetryProvider,
    )
    from shifu.shared.core.interfaces import CodeRubricAssessorProvider
    from shifu.shared.core.interfaces import AccountActivityProvider
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )


_HANDOFF_CAPABILITY = 'learning-code-assessment'
_UNAVAILABLE = 'Code assessment is unavailable.'


@dataclass(slots=True)
class _Execution:
    raw_input: object
    official: OfficialRunInput | None = None
    handoff_ref: str | None = None
    prepared: PreparedCodeActivityEvaluation | None = None
    assessment: CodeRubricAssessmentInput | None = None
    decisions: tuple[CodeQuestionAssessmentDecisions, ...] = ()
    failure: bool = False
    completion_emitted: bool = False


class EvaluateCodeActivityWorkflow(Workflow):
    """Run the Jev provider directly inside its visible native workflow graph."""

    def __init__(
        self,
        prepare_use_case: PrepareCodeActivityEvaluationUseCase,
        evaluate_use_case: EvaluateChoiceActivityUseCase,
        fail_use_case: FailCodeActivityEvaluationUseCase,
        persist_decision_use_case: PersistActivityRubricDecisionUseCase,
        assessor: CodeRubricAssessorProvider,
        handoffs: AgentOSHandoffStore,
        account_activity_provider: AccountActivityProvider,
        attempt_account_id_resolver: Callable[[str], str | None],
        observability: LangfuseTelemetryProvider | None = None,
        telemetry_provider: TelemetryProvider | None = None,
    ) -> None:
        self._prepare_use_case = prepare_use_case
        self._evaluate_use_case = evaluate_use_case
        self._fail_use_case = fail_use_case
        self._persist_decision_use_case = persist_decision_use_case
        self._assessor = assessor
        self._account_activity_provider = account_activity_provider
        self._attempt_account_id_resolver = attempt_account_id_resolver
        self._observability: LangfuseTelemetryProvider | None = observability
        self._telemetry_provider = telemetry_provider
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
            self._persist_decision_use_case,
            self._assessor,
            self._handoffs,
            self._account_activity_provider,
            self._attempt_account_id_resolver,
            self._observability,
            self._telemetry_provider,
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

    def _prepare(self, step_input: StepInput) -> StepOutput:
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
                with self._account_activity_scope(official.attempt_id):
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
                    model_profile='jev-rubric',
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
                question_decisions: list[CodeQuestionAssessmentDecisions] = []
                saved_decisions = {
                    decision.question_key: decision
                    for decision in prepared.rubric_decisions
                }
                for item in prepared.questions:
                    with self._account_activity_scope(
                        prepared.attempt_id
                    ) as account_id:
                        saved_decision = saved_decisions.get(item.question_key)
                        effect_id = uuid5(
                            NAMESPACE_URL,
                            'shifu:learning:code-rubric:'
                            f'{prepared.attempt_id}:{prepared.run_id}:{item.question_key}',
                        )
                        with self._account_activity_provider.external_effect(
                            account_id,
                            effect_id,
                            'learning.code-rubric.assess',
                            allow_durable_result_recovery=saved_decision is not None,
                        ) as should_assess:
                            if saved_decision is not None:
                                rubric_decisions = saved_decision.decisions
                            else:
                                self._require_external_assessment(should_assess)
                                rubric_decisions = self._assessor.assess(
                                    item.assessment_input
                                )
                                self._persist_decision_use_case.execute(
                                    prepared.attempt_id,
                                    prepared.run_id,
                                    item.question_key,
                                    'code',
                                    rubric_decisions,
                                )
                    question_decisions.append(
                        CodeQuestionAssessmentDecisions(
                            question_key=item.question_key,
                            decisions=rubric_decisions,
                        )
                    )
                execution.decisions = tuple(question_decisions)
            elif execution.assessment is not None:
                return self._assess_handoff_execution(execution)
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

    def _assess_handoff_execution(self, execution: _Execution) -> StepOutput:
        if execution.handoff_ref is None or execution.assessment is None:
            execution.failure = True
            return StepOutput(content='unavailable')
        decisions = self._assessor.assess(execution.assessment)
        self._handoffs.complete(
            execution.handoff_ref,
            capability=_HANDOFF_CAPABILITY,
            result_value=decisions,
        )
        execution.decisions = (
            CodeQuestionAssessmentDecisions(question_key='', decisions=decisions),
        )
        return StepOutput(content='assessed')

    @staticmethod
    def _require_external_assessment(should_assess: bool) -> None:
        if not should_assess:
            raise ServiceUnavailableError(_UNAVAILABLE)

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
                    with self._account_activity_scope(prepared.attempt_id):
                        self._fail_use_case.execute(
                            prepared.attempt_id, prepared.run_id
                        )
                except Exception:  # noqa: BLE001 - persist only safe failure state.
                    raise ServiceUnavailableError(_UNAVAILABLE) from None
                return StepOutput(content='failed')
            try:
                with self._account_activity_scope(prepared.attempt_id):
                    committed = self._evaluate_use_case.execute(
                        prepared.attempt_id,
                        prepared.run_id,
                        execution.decisions,
                    )
            except Exception:  # noqa: BLE001 - only a safe class crosses the run boundary.
                raise ServiceUnavailableError(_UNAVAILABLE) from None
            if not committed:
                return StepOutput(content='stale')
            self._emit_completion_telemetry(execution, prepared.run_id)
            return StepOutput(content='completed')
        if execution.failure:
            return StepOutput(content='unavailable')
        return StepOutput(content='complete')

    @contextmanager
    def _account_activity_scope(self, attempt_id: str) -> Generator[str]:
        account_id = self._attempt_account_id_resolver(attempt_id)
        if account_id is None:
            raise ServiceUnavailableError(_UNAVAILABLE)
        with self._account_activity_provider.activity(account_id):
            if self._attempt_account_id_resolver(attempt_id) != account_id:
                raise ServiceUnavailableError(_UNAVAILABLE)
            yield account_id

    def _emit_completion_telemetry(
        self,
        execution: _Execution,
        run_id: str,
    ) -> None:
        if self._telemetry_provider is None or execution.completion_emitted:
            return
        execution.completion_emitted = True
        try:
            self._telemetry_provider.emit(
                {
                    'level': 'INFO',
                    'event': 'learning.evaluation.completed',
                    'run_id': run_id,
                    'operation': 'evaluation.complete',
                    'result': 'success',
                }
            )
        except Exception:  # noqa: BLE001 - telemetry must not change workflow result.
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
