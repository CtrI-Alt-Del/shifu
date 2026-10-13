import hashlib
import json
from dataclasses import asdict, dataclass, replace
from collections.abc import Callable
from contextvars import ContextVar
from math import isfinite
from threading import Lock
from time import perf_counter
from uuid import uuid4
from typing import ClassVar, Literal, cast

from agno.exceptions import ModelProviderError, OutputCheckError, SchemaMismatchError
from agno.workflow.loop import Loop
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow
from agno.run.workflow import WorkflowRunOutput
from agno.workflow.types import StepInput, StepOutput, WorkflowMetrics
from pydantic import ValidationError
from openai import APIStatusError

from shifu.intelligence.ai.agno.agents.mentor_writer_agent import MentorWriterAgent
from shifu.intelligence.ai.agno.models.mentor_openai_chat import (
    configure_mentor_sdk_logging,
    mentor_transport_failure_scope,
)
from shifu.intelligence.ai.data.mentor_inference_usage import (
    assert_inference_ready,
    inference_guard_scope,
    inference_usage_scope,
    report_inference_usage,
)
from shifu.intelligence.core.domain.enums import MentorWorkflowStep
from shifu.intelligence.core.domain.structures.mentor_inference_usage import (
    MentorInferenceUsage,
)
from shifu.intelligence.ai.agno.outputs.mentor_answer_block_output import (
    MentorAnswerBlockOutput,
)
from shifu.intelligence.core.domain.structures.mentor_generation_request import (
    MentorGenerationRequest,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.intelligence.core.domain.structures.mentor_review_result import (
    MentorReviewResult,
)
from shifu.intelligence.core.interfaces.mentor_review_provider import (
    MentorReviewProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


@dataclass
class _Execution:
    request: MentorGenerationRequest
    usage_recorder: Callable[[MentorInferenceUsage], None] | None
    progress_recorder: Callable[[MentorWorkflowStep], None] | None
    correlation_id: str
    version: int = 0
    candidate: MentorResponseBlock | None = None
    review: MentorReviewResult | None = None


class AgnoAnswerMentorMessageWorkflow(Workflow):
    _MAX_VERSIONS: ClassVar[int] = 2
    _UNAVAILABLE: ClassVar[str] = 'Resposta do Mentor temporariamente indisponível.'
    _reviewer: MentorReviewProvider
    _reviewer_profile: Literal['jev', 'mentor-reviewer']
    _execution_lock: Lock
    _fallback: Workflow | None
    _telemetry: LangfuseMentorTelemetryProvider
    _last_profile: str
    _writer: Workflow
    _execution: ContextVar[_Execution]

    def __init__(
        self,
        writer: MentorWriterAgent,
        reviewer: MentorReviewProvider,
        *,
        fallback_writer: MentorWriterAgent | None = None,
        fallback_privacy_verified: bool = False,
        telemetry: LangfuseMentorTelemetryProvider | None = None,
        reviewer_profile: Literal['jev', 'mentor-reviewer'] = 'jev',
    ) -> None:
        super().__init__(
            name='answer-mentor-message',
            steps=[
                Loop(
                    name='write-review-cycle',
                    steps=[
                        Step(
                            name='write-answer',
                            executor=self._write_step,
                            max_retries=0,
                        ),
                        Step(
                            name='review-answer',
                            executor=self._review_step,
                            max_retries=0,
                        ),
                    ],
                    max_iterations=self._MAX_VERSIONS,
                    end_condition=self._review_complete,
                )
            ],
            telemetry=False,
            store_events=False,
            store_executor_outputs=False,
        )
        configure_mentor_sdk_logging()
        self._telemetry = telemetry or LangfuseMentorTelemetryProvider()
        self._reviewer = reviewer
        self._reviewer_profile = reviewer_profile
        self._execution_lock = Lock()
        self._execution = ContextVar('mentor_workflow_execution')
        self._last_profile = 'gpt-6-luna'
        self._writer = Workflow(
            name='answer-mentor-message-writer',
            steps=[Step(name='draft-answer', agent=writer, max_retries=0)],
            telemetry=False,
            store_events=False,
            store_executor_outputs=False,
        )
        if fallback_writer is not None and not fallback_privacy_verified:
            raise ValueError(
                'Fallback requires effective ZDR and disabled prompt logging'
            )
        self._fallback = (
            Workflow(
                name='answer-mentor-message-technical-fallback',
                steps=[
                    Step(
                        name='write-fallback-answer',
                        agent=fallback_writer,
                        max_retries=0,
                    )
                ],
                telemetry=False,
                store_events=False,
                store_executor_outputs=False,
            )
            if fallback_writer is not None
            else None
        )

    def run(  # pyright: ignore[reportIncompatibleMethodOverride] - Core capability deliberately hides native Agno transport.
        self,
        request: MentorGenerationRequest,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
        inference_guard: Callable[[], None] | None = None,
        progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
    ) -> MentorResponseBlock:
        # Native Agent mutable run/session state must never cross concurrent learners.
        with self._execution_lock, inference_guard_scope(inference_guard):
            assert_inference_ready()
            execution = _Execution(
                request, usage_recorder, progress_recorder, str(uuid4())
            )
            token = self._execution.set(execution)
            try:
                # Only an ID and closed step outcomes enter the outer Agno graph.
                result = super().run(input=request.attempt_id)
                if (
                    not result.has_completed()
                    or execution.review is None
                    or not execution.review.approved
                    or execution.candidate is None
                ):
                    raise ServiceUnavailableError(self._UNAVAILABLE)
                return execution.candidate
            finally:
                self._execution.reset(token)

    def _write_step(self, step_input: StepInput) -> StepOutput:
        del step_input
        execution = self._execution.get()
        request = execution.request
        started = perf_counter()
        prefix = (
            f'{request.attempt_id}:{len(request.approved_blocks)}:{execution.version}'
        )
        if execution.progress_recorder is not None:
            execution.progress_recorder(MentorWorkflowStep.WRITE_ANSWER)
        with inference_usage_scope(prefix, execution.usage_recorder):
            execution.candidate = self._write(request)
        execution.review = None
        self._telemetry.record_answer(
            attempt_id=request.attempt_id,
            block_key=execution.candidate.block_key,
            version=execution.version,
            correlation_id=execution.correlation_id,
            answer=execution.candidate.content,
        )
        self._telemetry.emit(
            'generate',
            correlation_id=execution.correlation_id,
            profile=self._last_profile,
            duration_ms=(perf_counter() - started) * 1000,
            counts={'blocks': 1},
            outcome='passed',
        )
        return StepOutput(content='generated')

    def _review_step(self, step_input: StepInput) -> StepOutput:
        del step_input
        execution = self._execution.get()
        request = execution.request
        candidate = execution.candidate
        if candidate is None:
            raise ServiceUnavailableError(self._UNAVAILABLE)
        started = perf_counter()
        prefix = (
            f'{request.attempt_id}:{len(request.approved_blocks)}:{execution.version}'
        )
        if execution.progress_recorder is not None:
            execution.progress_recorder(MentorWorkflowStep.REVIEW_ANSWER)
        with inference_usage_scope(prefix, execution.usage_recorder):
            review = self._reviewer.review(request, candidate)
        execution.review = review
        self._telemetry.record_review(
            attempt_id=request.attempt_id,
            block_key=candidate.block_key,
            version=execution.version,
            correlation_id=execution.correlation_id,
            answer=candidate.content,
            review=review,
        )
        execution.version += 1
        self._telemetry.emit(
            'review',
            correlation_id=execution.correlation_id,
            profile=self._reviewer_profile,
            duration_ms=(perf_counter() - started) * 1000,
            counts={},
            outcome='passed' if review.approved else 'abstained',
        )
        if review.approved:
            return StepOutput(content='approved')
        if review.correction is None:
            return StepOutput(content='rejected')
        execution.request = replace(request, correction=review.correction)
        return StepOutput(content='revise')

    @staticmethod
    def _review_complete(outputs: list[StepOutput]) -> bool:
        return outputs[-1].content != 'revise'

    def _run_writer(self, payload: str) -> WorkflowRunOutput:
        self._last_profile = 'gpt-6-luna'
        assert_inference_ready()
        received_tokens: int | None = None
        try:
            with mentor_transport_failure_scope() as failure:
                try:
                    result = self._writer.run(input=payload)
                    failure.raise_if_failed()
                finally:
                    received_tokens = failure.used_tokens
        except ModelProviderError as error:
            report_inference_usage(
                'writer:0',
                'gpt-6-luna',
                received_tokens
                if received_tokens is not None
                else self._failure_tokens(error),
            )
            if self._fallback is None or not (
                error.status_code in {408, 429} or 500 <= error.status_code < 600
            ):
                raise ServiceUnavailableError(self._UNAVAILABLE) from None
            self._last_profile = 'openrouter-deepseek'
            assert_inference_ready()
            received_tokens = None
            try:
                with mentor_transport_failure_scope() as failure:
                    try:
                        result = self._fallback.run(input=payload)
                        failure.raise_if_failed()
                    finally:
                        received_tokens = failure.used_tokens
            except ModelProviderError as fallback_error:
                report_inference_usage(
                    'writer:1',
                    self._last_profile,
                    received_tokens
                    if received_tokens is not None
                    else self._failure_tokens(fallback_error),
                )
                raise ServiceUnavailableError(self._UNAVAILABLE) from None
            except Exception:
                report_inference_usage('writer:1', self._last_profile, received_tokens)
                raise
        except Exception:
            report_inference_usage('writer:0', 'gpt-6-luna', received_tokens)
            raise
        input_tokens, output_tokens, tokens, cost_usd = self._writer_usage(result)
        report_inference_usage(
            'writer:1' if self._last_profile == 'openrouter-deepseek' else 'writer:0',
            self._last_profile,
            tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
        return result

    @staticmethod
    def _writer_usage(
        result: WorkflowRunOutput,
    ) -> tuple[int | None, int | None, int | None, float | None]:
        metrics = cast('object', result.metrics)
        if not isinstance(metrics, WorkflowMetrics) or not metrics.steps:
            return None, None, None, None
        input_counts: list[int] = []
        output_counts: list[int] = []
        total_counts: list[int] = []
        costs: list[float] = []
        costs_complete = True
        for step in metrics.steps.values():
            if step.metrics is None:
                return None, None, None, None
            usage = step.metrics
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            total_tokens = usage.total_tokens
            if (
                isinstance(input_tokens, bool)
                or input_tokens < 0
                or isinstance(output_tokens, bool)
                or output_tokens < 0
                or isinstance(total_tokens, bool)
                or total_tokens < 0
                or total_tokens <= 0
                or input_tokens + output_tokens != total_tokens
            ):
                return None, None, None, None
            input_counts.append(input_tokens)
            output_counts.append(output_tokens)
            total_counts.append(total_tokens)
            cost = usage.cost
            if cost is None or isinstance(cost, bool) or not isfinite(cost) or cost < 0:
                costs_complete = False
            else:
                costs.append(float(cost))
        return (
            sum(input_counts),
            sum(output_counts),
            sum(total_counts),
            sum(costs) if costs_complete else None,
        )

    @staticmethod
    def _failure_tokens(error: ModelProviderError) -> int | None:
        cause = error.__cause__
        if not isinstance(cause, APIStatusError):
            return None
        try:
            body: object = cause.response.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None
        usage: object = cast('dict[str, object]', body).get('usage')
        if not isinstance(usage, dict):
            return None
        values: tuple[object, ...] = tuple(
            cast('dict[str, object]', usage).get(key)
            for key in (
                'prompt_tokens',
                'completion_tokens',
                'total_tokens',
            )
        )
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in values
        ):
            return None
        prompt, completion, total = cast('tuple[int, int, int]', values)
        return total if prompt + completion == total else None

    def _write(self, request: MentorGenerationRequest) -> MentorResponseBlock:
        block_key = hashlib.sha256(
            f'{request.attempt_id}:{request.requested_part}'.encode()
        ).hexdigest()[:32]
        ordinal = len(request.approved_blocks)
        payload = asdict(request)
        payload['block_key'] = block_key
        payload['ordinal'] = ordinal
        try:
            response = self._run_writer(
                json.dumps(payload, default=str, ensure_ascii=False)
            )
            output = (
                MentorAnswerBlockOutput.model_validate_json(response.content)
                if isinstance(response.content, str)
                else MentorAnswerBlockOutput.model_validate(response.content)
            )
        except (ValidationError, OutputCheckError, SchemaMismatchError):
            raise ServiceUnavailableError(self._UNAVAILABLE) from None
        except Exception:  # noqa: BLE001 - SDK failures must be sanitized before durable job reporting.
            # SDK failures cannot disclose prompt/candidate/credentials in durable errors.
            raise ServiceUnavailableError(self._UNAVAILABLE) from None
        if not response.has_completed():
            raise ServiceUnavailableError(self._UNAVAILABLE)
        if (
            output.block_key != block_key
            or output.ordinal != ordinal
            or not output.content.strip()
        ):
            raise ServiceUnavailableError(self._UNAVAILABLE)
        return MentorResponseBlock(
            block_key=block_key,
            ordinal=ordinal,
            intent=output.intent,
            content=output.content,
        )
