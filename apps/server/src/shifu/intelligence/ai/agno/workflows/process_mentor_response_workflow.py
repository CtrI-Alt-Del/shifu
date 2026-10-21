"""Durable response graph with private per-run state kept outside AgentOS outputs."""

from __future__ import annotations

from asyncio import to_thread
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass, field, replace
from datetime import timedelta
from json import dumps
from math import isfinite
from threading import Event, Thread
from time import perf_counter
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from agno.metrics import RunMetrics
from agno.run.base import RunStatus
from agno.workflow import Loop
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.intelligence.ai.agno.models.mentor_openai_chat import (
    mentor_transport_failure_scope,
)
from shifu.intelligence.ai.data.mentor_inference_usage import (
    inference_guard_scope,
    inference_usage_scope,
    report_inference_usage,
)
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentSource,
    MentorGenerationRequest,
    MentorResponseBlock,
    MentorReviewResult,
    PreparedMentorResponse,
)
from shifu.intelligence.providers.telemetry.mentor_telemetry_correlation import (
    mentor_telemetry_correlation,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.messaging.agentos.workflow_helpers import copy_agent

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence

    from agno.run.agent import RunOutput

    from shifu.intelligence.ai.agno.agents import (
        MentorAttachmentAnswerAgent,
        MentorReviewerAgent,
        MentorWriterAgent,
    )
    from shifu.intelligence.core.domain.structures import MentorInferenceUsage
    from shifu.intelligence.core.interfaces import MentorTelemetryProvider
    from shifu.intelligence.core.use_cases import (
        AssertMentorResponseCurrentUseCase,
        FailMentorResponseUseCase,
        PrepareMentorResponseUseCase,
        PublishMentorResponseBlockUseCase,
        RecordMentorInferenceUsageUseCase,
        RecordMentorResponseProgressUseCase,
        ReleaseMentorResponseClaimUseCase,
        RenewMentorResponseClaimUseCase,
        SummarizeMentorSessionContextUseCase,
        UpdateLearnerMemoriesUseCase,
    )
    from shifu.intelligence.core.use_cases.finalize_mentor_response_use_case import (
        FinalizeMentorResponseUseCase,
    )
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )
    from shifu.shared.providers.system_identifier_provider import (
        SystemIdentifierProvider,
    )


_UNAVAILABLE = 'Mentor response processing is unavailable.'
_HANDOFF_CAPABILITY = 'process-mentor-response'
_MAX_REVIEW_ITERATIONS = 3


class _Input(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    attempt_id: str = Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
    event_id: str | None = Field(default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')


class _StepReference(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    handoff: str = Field(min_length=32, max_length=128)
    decision: Literal['continue', 'retry', 'done']
    iteration: int = Field(default=0, ge=0, le=_MAX_REVIEW_ITERATIONS)


@dataclass(slots=True)
class _ExecutionState:
    prepared: PreparedMentorResponse | None
    status: MentorResponseStatus
    approved_blocks: tuple[MentorResponseBlock, ...] = ()
    candidate: MentorResponseBlock | None = None
    correction: str | None = None
    approved: bool = False
    iteration: int = 0
    telemetry_correlation_id: str = field(default_factory=lambda: uuid4().hex)


class ProcessMentorResponseWorkflow(Workflow):
    """Run Core phases and direct, bounded Agent calls without storing private data."""

    def __init__(
        self,
        *,
        summarize_use_case: SummarizeMentorSessionContextUseCase,
        update_memories_use_case: UpdateLearnerMemoriesUseCase,
        prepare_use_case: PrepareMentorResponseUseCase,
        publish_block_use_case: PublishMentorResponseBlockUseCase,
        assert_current_use_case: AssertMentorResponseCurrentUseCase,
        renew_claim_use_case: RenewMentorResponseClaimUseCase,
        release_claim_use_case: ReleaseMentorResponseClaimUseCase,
        fail_use_case: FailMentorResponseUseCase,
        record_usage_use_case: RecordMentorInferenceUsageUseCase,
        record_progress_use_case: RecordMentorResponseProgressUseCase,
        writer_agent: MentorWriterAgent,
        attachment_answer_agent: MentorAttachmentAnswerAgent,
        reviewer_agent: MentorReviewerAgent,
        finalizer: FinalizeMentorResponseUseCase,
        identifier_provider: SystemIdentifierProvider,
        handoffs: AgentOSHandoffStore,
        telemetry: MentorTelemetryProvider | None = None,
    ) -> None:
        self._summarize = summarize_use_case
        self._update_memories = update_memories_use_case
        self._prepare = prepare_use_case
        self._publish_block = publish_block_use_case
        self._assert_current = assert_current_use_case
        self._renew_claim = renew_claim_use_case
        self._release_claim = release_claim_use_case
        self._fail = fail_use_case
        self._record_usage = record_usage_use_case
        self._record_progress = record_progress_use_case
        self._writer = writer_agent
        self._attachment_answer = attachment_answer_agent
        self._reviewer = reviewer_agent
        self._finalizer = finalizer
        self._identifier_provider = identifier_provider
        self._telemetry: MentorTelemetryProvider | None = telemetry
        self._handoffs = handoffs
        super().__init__(
            id='intelligence-process-mentor-response',
            name='Process Mentor Response',
            steps=[
                Step(
                    name='summarize-conversation-context',
                    executor=self._summarize_context,
                    max_retries=0,
                ),
                Step(
                    name='update-learner-memories',
                    executor=self._update_learner_memories,
                    max_retries=0,
                ),
                Step(
                    name='prepare-and-publish-local-response',
                    executor=self._prepare_and_publish,
                    max_retries=0,
                ),
                Loop(
                    name='write-and-review-response',
                    steps=[
                        Step(
                            name='write-and-review-candidate',
                            executor=self._write_and_review,
                            max_retries=0,
                        )
                    ],
                    end_condition=self._review_complete,
                    max_iterations=_MAX_REVIEW_ITERATIONS,
                    forward_iteration_output=True,
                ),
                Step(
                    name='publish-approved-response-and-finalize',
                    executor=self._publish_and_finalize,
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
    ) -> ProcessMentorResponseWorkflow:
        workflow = ProcessMentorResponseWorkflow(
            summarize_use_case=self._summarize,
            update_memories_use_case=self._update_memories,
            prepare_use_case=self._prepare,
            publish_block_use_case=self._publish_block,
            assert_current_use_case=self._assert_current,
            renew_claim_use_case=self._renew_claim,
            release_claim_use_case=self._release_claim,
            fail_use_case=self._fail,
            record_usage_use_case=self._record_usage,
            record_progress_use_case=self._record_progress,
            writer_agent=copy_agent(self._writer),
            attachment_answer_agent=copy_agent(self._attachment_answer),
            reviewer_agent=copy_agent(self._reviewer),
            finalizer=self._finalizer,
            identifier_provider=self._identifier_provider,
            handoffs=self._handoffs,
            telemetry=self._telemetry,
        )
        workflow.db = self.db
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    async def _summarize_context(self, step_input: StepInput) -> StepOutput:
        """Run the summarization off the event loop so live progress keeps streaming."""
        return await to_thread(self._summarize_context_blocking, step_input)

    def _summarize_context_blocking(self, step_input: StepInput) -> StepOutput:
        """Summarize a long conversation first; this step never fails the answer run."""
        try:
            raw = step_input.input
            request = (
                _Input.model_validate_json(raw, strict=True)
                if isinstance(raw, str)
                else _Input.model_validate(raw, strict=True)
            )
            self._summarize.execute(
                request.attempt_id, request.event_id or request.attempt_id
            )
        except Exception:  # noqa: BLE001 - prepare validates the input and decides the outcome.
            return StepOutput(content='summary-skipped')
        return StepOutput(content='summary-done')

    async def _update_learner_memories(self, step_input: StepInput) -> StepOutput:
        """Analyze the learner's statements off the event loop (spaCy and scikit-learn)."""
        return await to_thread(self._update_learner_memories_blocking, step_input)

    def _update_learner_memories_blocking(self, step_input: StepInput) -> StepOutput:
        """Create or update learner memories; this step never fails the answer run."""
        try:
            raw = step_input.input
            request = (
                _Input.model_validate_json(raw, strict=True)
                if isinstance(raw, str)
                else _Input.model_validate(raw, strict=True)
            )
            self._update_memories.execute(
                request.attempt_id, request.event_id or request.attempt_id
            )
        except Exception:  # noqa: BLE001 - prepare validates the input and decides the outcome.
            return StepOutput(content='memories-skipped')
        return StepOutput(content='memories-done')

    def _prepare_and_publish(self, step_input: StepInput) -> StepOutput:
        try:
            raw = step_input.input
            request = (
                _Input.model_validate_json(raw, strict=True)
                if isinstance(raw, str)
                else _Input.model_validate(raw, strict=True)
            )
        except (ValidationError, ValueError, TypeError):
            raise ServiceUnavailableError(_UNAVAILABLE) from None

        owner = request.event_id or request.attempt_id
        try:
            prepared = self._prepare.execute(request.attempt_id, owner)
            if prepared is None:
                state = _ExecutionState(
                    prepared=None, status=MentorResponseStatus.CANCELLED
                )
                self._release_claim.execute(request.attempt_id, owner)
                return self._store(state, 'done')
            approved = (
                list(prepared.attachment_request.approved_blocks)
                if prepared.attachment_request
                else []
            )
            for block in prepared.local_blocks:
                published = self._publish_block.execute(
                    prepared.attempt_id,
                    owner,
                    block,
                    prepared.context,
                )
                self._assert_published(published)
                if all(existing.block_key != block.block_key for existing in approved):
                    approved.append(block)
            if prepared.attachment_request is not None:
                prepared = replace(
                    prepared,
                    attachment_request=replace(
                        prepared.attachment_request,
                        approved_blocks=tuple(approved),
                    ),
                )
            return self._store(
                _ExecutionState(
                    prepared=prepared,
                    status=MentorResponseStatus.PROCESSING,
                    approved_blocks=tuple(approved),
                ),
                'continue',
            )
        except Exception:  # noqa: BLE001 - translate private boundary failures.
            status = self._fail_response(request.attempt_id, owner)
            self._release_claim_safely(request.attempt_id, owner)
            return self._store(_ExecutionState(prepared=None, status=status), 'done')

    def _write_and_review(self, step_input: StepInput) -> StepOutput:
        try:
            reference = self._read_reference(step_input.get_last_step_content())
            request = self._request_for_step(step_input)
            state = self._consume_or_recover(reference, request)
        except Exception:  # noqa: BLE001 - opaque handoff errors are sanitized.
            raise ServiceUnavailableError(_UNAVAILABLE) from None
        return self._write_state(state)

    def _write_state(self, state: _ExecutionState) -> StepOutput:
        # This random token stays in the private handoff and ContextVar only. It
        # connects native step observations without exporting business identifiers.
        with mentor_telemetry_correlation(state.telemetry_correlation_id):
            return self._write_state_correlated(state)

    def _write_state_correlated(self, state: _ExecutionState) -> StepOutput:
        if (
            state.prepared is None
            or state.status is not MentorResponseStatus.PROCESSING
        ):
            return self._store(state, 'done')
        request = state.prepared.attachment_request
        if request is None or request.attachment_context is None:
            return self._store(state, 'done')

        owner = state.prepared.execution_owner
        attempt_id = state.prepared.attempt_id
        next_iteration = state.iteration + 1
        try:
            request = replace(
                request,
                approved_blocks=state.approved_blocks,
                correction=state.correction,
            )
            usage_recorder = self._usage_recorder(attempt_id, owner, 'generated-0')
            self._record_progress.execute(
                attempt_id, owner, MentorWorkflowStep.WRITE_ANSWER
            )
            with self._inference_guard(attempt_id, owner):
                if request.attachment_context is not None:
                    with inference_usage_scope(
                        'generated-0',
                        usage_recorder,
                    ):
                        answer = self._attachment_answer.answer(
                            request.requested_part,
                            request.attachment_context,
                            request.memories,
                        )
                    candidate = MentorResponseBlock(
                        block_key='generated-0',
                        ordinal=len(state.approved_blocks),
                        intent=None,
                        content=answer.answer,
                        sources=self._attachment_answer.domain_sources(answer),
                    )
                else:
                    candidate = self._write_general_answer(
                        request, attempt_id, owner, len(state.approved_blocks)
                    )
            self._record_progress.execute(
                attempt_id, owner, MentorWorkflowStep.REVIEW_ANSWER
            )
            with (
                self._inference_guard(attempt_id, owner),
                inference_usage_scope(
                    'generated-0',
                    usage_recorder,
                ),
            ):
                review = self._review_candidate(
                    request, candidate, state.telemetry_correlation_id
                )
            updated = replace(
                state,
                candidate=candidate if review.approved else None,
                correction=review.correction,
                approved=review.approved,
                iteration=next_iteration,
            )
            decision = 'done' if review.approved else 'retry'
            return self._store(updated, decision)
        except Exception:  # noqa: BLE001 - private Agent/provider failures fail closed.
            status = self._fail_response(attempt_id, owner)
            self._release_claim_safely(attempt_id, owner)
            return self._store(
                replace(state, status=status, candidate=None, approved=False), 'done'
            )

    def _review_candidate(
        self,
        request: MentorGenerationRequest,
        candidate: MentorResponseBlock,
        correlation_id: str,
    ) -> MentorReviewResult:
        started = perf_counter()
        outcome: Literal['passed', 'failed', 'abstained'] = 'failed'
        criteria_count = 0
        try:
            review = self._reviewer.review(request, candidate)
            self._assert_review_result(review)
            criteria_count = len(review.criteria)
            outcome = 'passed' if review.approved else 'abstained'
            return review
        finally:
            if self._telemetry is not None:
                with suppress(Exception):
                    self._telemetry.emit(
                        'review',
                        correlation_id=correlation_id,
                        profile='mentor-reviewer',
                        duration_ms=(perf_counter() - started) * 1000,
                        counts={'criteria': criteria_count},
                        outcome=outcome,
                    )

    def _write_general_answer(
        self,
        request: MentorGenerationRequest,
        attempt_id: str,
        owner: str,
        ordinal: int,
    ) -> MentorResponseBlock:
        from shifu.intelligence.ai.agno.outputs import MentorAnswerBlockOutput

        usage_recorder = self._usage_recorder(attempt_id, owner, 'generated-0')
        with inference_usage_scope('generated-0', usage_recorder):
            self._assert_current.execute(attempt_id, owner)
            response: RunOutput | None = None
            received_tokens: int | None = None
            try:
                with mentor_transport_failure_scope() as failure:
                    try:
                        response = self._writer.run(  # pyright: ignore[reportUnknownMemberType] - Agno Agent lacks complete stubs.
                            input=dumps(
                                {'request': asdict(request)}, ensure_ascii=False
                            )
                        )
                        failure.raise_if_failed()
                    finally:
                        received_tokens = failure.used_tokens
            except Exception:
                report_inference_usage('writer:0', 'mentor-writer', received_tokens)
                raise
            if response is None:  # pyright: ignore[reportUnnecessaryComparison] - keep the opaque provider boundary defensive.
                raise ServiceUnavailableError(_UNAVAILABLE)
            input_tokens, output_tokens, total_tokens, cost = self._usage_fields(
                response
            )
            report_inference_usage(
                'writer:0',
                'mentor-writer',
                total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
            if response.status != RunStatus.completed:
                raise ServiceUnavailableError
        output = response.content
        parsed = (
            MentorAnswerBlockOutput.model_validate_json(output, strict=True)
            if isinstance(output, str)
            else MentorAnswerBlockOutput.model_validate(output, strict=True)
        )
        sources = tuple(
            MentorAttachmentSource(
                attachment_id=source.attachment_id,
                chunk_id=source.chunk_id,
                page_number=source.page_number,
                locator=source.locator,
            )
            for source in parsed.sources
        )
        return MentorResponseBlock(
            block_key='generated-0',
            ordinal=ordinal,
            intent=parsed.intent,
            content=parsed.content,
            sources=sources,
        )

    @staticmethod
    def _review_complete(outputs: Sequence[StepOutput]) -> bool:
        if not outputs or not isinstance(outputs[-1].content, str):
            return True
        try:
            return (
                _StepReference.model_validate_json(
                    outputs[-1].content, strict=True
                ).decision
                != 'retry'
            )
        except (ValidationError, ValueError, TypeError):
            return True

    def _publish_and_finalize(self, step_input: StepInput) -> StepOutput:
        try:
            reference = self._read_reference(step_input.get_last_step_content())
            request = self._request_for_step(step_input)
            state = self._consume_or_recover(reference, request)
        except Exception:  # noqa: BLE001 - opaque handoff errors are sanitized.
            raise ServiceUnavailableError(_UNAVAILABLE) from None
        if (
            state.prepared is None
            or state.status is not MentorResponseStatus.PROCESSING
        ):
            return StepOutput(content=state.status.value)

        prepared = state.prepared
        owner = prepared.execution_owner
        try:
            request = prepared.attachment_request
            if request is not None:
                if not state.approved or state.candidate is None:
                    status = self._fail_response(prepared.attempt_id, owner)
                    return StepOutput(content=status.value)
                if not self._publish_block.execute(
                    prepared.attempt_id,
                    owner,
                    state.candidate,
                    prepared.context,
                ):
                    status = self._fail_response(prepared.attempt_id, owner)
                    return StepOutput(content=status.value)
                if all(
                    existing.block_key != state.candidate.block_key
                    for existing in state.approved_blocks
                ):
                    state.approved_blocks = (
                        *state.approved_blocks,
                        state.candidate,
                    )
            if not state.approved_blocks:
                status = self._fail_response(prepared.attempt_id, owner)
                return StepOutput(content=status.value)
            content = '\n\n'.join(
                block.content
                for block in sorted(
                    state.approved_blocks, key=lambda item: item.ordinal
                )
            )
            self._assert_current.execute(prepared.attempt_id, owner)
            finalized = self._finalizer.execute(
                prepared.account_id,
                prepared.session_id,
                prepared.learner_message_id,
                content,
                prepared.attempt_id,
                owner,
            )
            if not finalized:
                return StepOutput(
                    content=self._fail_response(prepared.attempt_id, owner).value
                )
            return StepOutput(content=MentorResponseStatus.COMPLETED.value)
        except Exception:  # noqa: BLE001 - sanitize private finalization failures.
            return StepOutput(
                content=self._fail_response(prepared.attempt_id, owner).value
            )
        finally:
            self._release_claim_safely(prepared.attempt_id, owner)

    @contextmanager
    def _inference_guard(self, attempt_id: str, owner: str) -> Generator[None]:
        stop = Event()
        lost = Event()

        def renew() -> None:
            while not stop.wait(30):
                try:
                    if not self._renew_claim.execute(attempt_id, owner):
                        lost.set()
                        return
                except Exception:  # noqa: BLE001 - renewal failure invalidates inference.
                    lost.set()
                    return

        worker = Thread(target=renew, daemon=True)
        worker.start()

        def assert_current() -> None:
            if lost.is_set():
                raise ServiceUnavailableError
            self._assert_current.execute(attempt_id, owner)

        try:
            with inference_guard_scope(assert_current):
                assert_current()
                yield
        finally:
            stop.set()
            worker.join(timeout=5)

    def _fail_response(self, attempt_id: str, owner: str) -> MentorResponseStatus:
        try:
            return self._fail.execute(attempt_id, owner, 'service_unavailable')
        except Exception:  # noqa: BLE001 - suppress private failure details.
            return MentorResponseStatus.FAILED

    def _usage_recorder(
        self, attempt_id: str, owner: str, block_key: str
    ) -> Callable[[MentorInferenceUsage], None]:
        prefix = f'{block_key}:'

        def record(usage: MentorInferenceUsage) -> None:
            call_key = (
                usage.call_key
                if usage.call_key.startswith(prefix)
                else prefix + usage.call_key
            )
            self._record_usage.execute(
                attempt_id,
                owner,
                replace(usage, call_key=call_key),
            )

        return record

    def _release_claim_safely(self, attempt_id: str, owner: str) -> None:
        try:
            self._release_claim.execute(attempt_id, owner)
        except Exception:  # noqa: BLE001 - claim cleanup is best effort.
            return

    def _store(
        self, state: _ExecutionState, decision: Literal['continue', 'retry', 'done']
    ) -> StepOutput:
        reference = self._handoffs.create(
            capability=_HANDOFF_CAPABILITY,
            input_value=state,
            ttl=timedelta(minutes=5),
        )
        return StepOutput(
            content=_StepReference(
                handoff=reference, decision=decision, iteration=state.iteration
            ).model_dump_json()
        )

    @staticmethod
    def _request_for_step(step_input: StepInput) -> _Input:
        raw = step_input.input
        return (
            _Input.model_validate_json(raw, strict=True)
            if isinstance(raw, str)
            else _Input.model_validate(raw, strict=True)
        )

    def _consume_or_recover(
        self, reference: _StepReference, request: _Input
    ) -> _ExecutionState:
        try:
            return self._consume(reference)
        except (KeyError, ServiceUnavailableError):
            owner = request.event_id or request.attempt_id
            prepared = self._prepare.execute(request.attempt_id, owner)
            if prepared is None:
                self._release_claim_safely(request.attempt_id, owner)
                return _ExecutionState(
                    prepared=None, status=MentorResponseStatus.CANCELLED
                )
            approved = (
                list(prepared.attachment_request.approved_blocks)
                if prepared.attachment_request is not None
                else []
            )
            for block in prepared.local_blocks:
                self._assert_published(
                    self._publish_block.execute(
                        prepared.attempt_id,
                        owner,
                        block,
                        prepared.context,
                    )
                )
                if all(existing.block_key != block.block_key for existing in approved):
                    approved.append(block)
            if prepared.attachment_request is not None:
                prepared = replace(
                    prepared,
                    attachment_request=replace(
                        prepared.attachment_request,
                        approved_blocks=tuple(approved),
                    ),
                )
            state = _ExecutionState(
                prepared=prepared,
                status=MentorResponseStatus.PROCESSING,
                approved_blocks=tuple(approved),
            )
            for _ in range(reference.iteration):
                if state.approved:
                    break
                output = self._write_state(state)
                recovered_reference = self._read_reference(output.content)
                state = self._consume(recovered_reference)
                if state.prepared is None:
                    break
            return state

    @staticmethod
    def _read_reference(content: object) -> _StepReference:
        if not isinstance(content, str):
            raise ServiceUnavailableError
        return _StepReference.model_validate_json(content, strict=True)

    def _consume(self, reference: _StepReference) -> _ExecutionState:
        value = self._handoffs.read_input(
            reference.handoff, capability=_HANDOFF_CAPABILITY
        )
        if not isinstance(value, _ExecutionState):
            raise ServiceUnavailableError
        return value

    @staticmethod
    def _assert_published(published: bool) -> None:
        if not published:
            raise ServiceUnavailableError

    @staticmethod
    def _assert_review_result(review: object) -> None:
        if type(review) is not MentorReviewResult:
            raise ServiceUnavailableError

    @staticmethod
    def _usage_fields(
        response: RunOutput,
    ) -> tuple[int | None, int | None, int | None, float | None]:
        metrics = response.metrics
        if not isinstance(metrics, RunMetrics):
            return None, None, None, None
        values = (metrics.input_tokens, metrics.output_tokens, metrics.total_tokens)
        if (
            any(type(value) is not int or value < 0 for value in values)
            or values[2] <= 0
            or values[0] + values[1] != values[2]
        ):
            return None, None, None, None
        cost = metrics.cost
        valid_cost = (
            float(cost)
            if cost is not None
            and type(cost) is not bool
            and isfinite(cost)
            and cost >= 0
            else None
        )
        return *values, valid_cost
