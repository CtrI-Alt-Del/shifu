import asyncio
import json
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from threading import Event, Thread
from typing import Self, cast
from typing import ClassVar

from agno.run.workflow import WorkflowRunOutput
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow, WorkflowSteps
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.intelligence.ai.agno.agents import MentorAttachmentVisionAgent
from shifu.intelligence.ai.data.mentor_inference_usage import (
    inference_guard_scope,
    inference_usage_scope,
)
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentExtraction,
    MentorInferenceUsage,
    PreparedMentorAttachment,
)
from shifu.intelligence.core.interfaces import MentorAttachmentExtractorProvider
from shifu.intelligence.core.use_cases import (
    CompleteMentorAttachmentUseCase,
    FailMentorAttachmentUseCase,
    PrepareMentorAttachmentUseCase,
    ReleaseMentorAttachmentClaimUseCase,
    RenewMentorAttachmentClaimUseCase,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.messaging.agentos.workflow_helpers import copy_agent


class _PreparationInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    attachment_id: str = Field(pattern=r'^[0-9A-HJKMNP-TV-Z]{26}$')
    generation: int = Field(ge=1)
    event_id: str | None = Field(default=None, pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')


@dataclass
class _Execution:
    request: _PreparationInput
    owner: str
    prepared: PreparedMentorAttachment | None = None
    extraction: MentorAttachmentExtraction | None = None
    completed: bool = False


class _ClaimHeartbeat:
    def __init__(
        self,
        renew_use_case: RenewMentorAttachmentClaimUseCase,
        attachment_id: str,
        generation: int,
        execution_owner: str,
    ) -> None:
        self._renew_use_case = renew_use_case
        self._attachment_id = attachment_id
        self._generation = generation
        self._execution_owner = execution_owner
        self._stop = Event()
        self._lost = Event()
        self._thread: Thread | None = None

    def __enter__(self) -> Self:
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    @property
    def lost(self) -> bool:
        return self._lost.is_set()

    def _run(self) -> None:
        while not self._stop.wait(30):
            renewed = self._renew_use_case.execute(
                self._attachment_id, self._generation, self._execution_owner
            )
            if not renewed:
                self._lost.set()
                return


class AgnoPrepareMentorAttachmentWorkflow(Workflow):
    _CLAIM_RENEW_INTERVAL: ClassVar[int] = 30

    def __init__(
        self,
        prepare_use_case: PrepareMentorAttachmentUseCase,
        complete_use_case: CompleteMentorAttachmentUseCase,
        fail_use_case: FailMentorAttachmentUseCase,
        renew_claim_use_case: RenewMentorAttachmentClaimUseCase,
        release_claim_use_case: ReleaseMentorAttachmentClaimUseCase,
        extractor_provider: MentorAttachmentExtractorProvider,
        vision_agent: MentorAttachmentVisionAgent,
        identifier_provider: IdentifierProvider,
        *,
        max_pdf_pages: int,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
    ) -> None:
        if max_pdf_pages < 1:
            raise ValueError('max_pdf_pages must be positive')
        self._execution: ContextVar[_Execution | None] = ContextVar(
            'prepare_mentor_attachment_execution', default=None
        )
        super().__init__(
            id='intelligence-prepare-mentor-attachment',
            name='prepare-mentor-attachment',
            steps=self._build_steps(asynchronous=True),
            telemetry=False,
            store_events=False,
            store_executor_outputs=False,
        )
        self._prepare_use_case = prepare_use_case
        self._complete_use_case = complete_use_case
        self._fail_use_case = fail_use_case
        self._renew_claim_use_case = renew_claim_use_case
        self._release_claim_use_case = release_claim_use_case
        self._extractor_provider = extractor_provider
        self._vision_agent = vision_agent
        self._identifier_provider = identifier_provider
        self._max_pdf_pages = max_pdf_pages
        self._usage_recorder = usage_recorder

    def _build_steps(self, *, asynchronous: bool) -> WorkflowSteps:
        phases = (
            ('prepare-private-source', self._prepare),
            ('extract-and-interpret', self._extract),
            ('commit-safe-coverage', self._complete),
        )
        return [
            Step(
                name=name,
                executor=(
                    self._async_phase(execute, name=name) if asynchronous else execute
                ),
                max_retries=0,
            )
            for name, execute in phases
        ]

    def _async_phase(
        self, execute: Callable[[StepInput], StepOutput], *, name: str
    ) -> Callable[[StepInput], Awaitable[StepOutput]]:
        @wraps(execute)
        async def execute_phase(step_input: StepInput) -> StepOutput:
            # Native queued runs use arun. Initialize state in its run task:
            # ContextVar assignments inside to_thread do not propagate back.
            execution = self._execution_for_step(step_input)
            try:
                return await asyncio.to_thread(execute, step_input)
            finally:
                if execution.completed:
                    self._execution.set(None)

        execute_phase.__name__ = f'prepare_mentor_attachment_{name.replace("-", "_")}'
        return execute_phase

    def deep_copy(
        self, *, update: dict[str, object] | None = None
    ) -> 'AgnoPrepareMentorAttachmentWorkflow':
        workflow = AgnoPrepareMentorAttachmentWorkflow(
            self._prepare_use_case,
            self._complete_use_case,
            self._fail_use_case,
            self._renew_claim_use_case,
            self._release_claim_use_case,
            self._extractor_provider,
            copy_agent(self._vision_agent),
            self._identifier_provider,
            max_pdf_pages=self._max_pdf_pages,
            usage_recorder=self._usage_recorder,
        )
        workflow.db = self.db
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    def run(  # pyright: ignore[reportIncompatibleMethodOverride] - This boundary accepts only a normalized event payload.
        self, input: object
    ) -> WorkflowRunOutput:
        workflow = self.deep_copy()
        workflow.steps = workflow._build_steps(asynchronous=False)  # noqa: SLF001 - Configure this class's per-call clone.
        request = self._parse_input(input)
        execution = _Execution(
            request=request,
            owner=request.event_id or request.attachment_id,
        )
        token = workflow._execution.set(execution)  # noqa: SLF001 - Scope state on this class's per-call clone.
        try:
            return Workflow.run(workflow, input=request.model_dump_json())
        except Exception:
            if not execution.completed:
                self._release_claim_use_case.execute(
                    request.attachment_id, request.generation, execution.owner
                )
            raise
        finally:
            workflow._execution.reset(token)  # noqa: SLF001 - Restore this class's per-call clone context.

    @staticmethod
    def _parse_input(raw: object) -> _PreparationInput:
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(raw, str) and isinstance(value, dict):
                payload = cast('dict[str, object]', value)
                generation = payload.get('generation')
                if isinstance(generation, str) and generation.isdecimal():
                    value = {**payload, 'generation': int(generation)}
            return _PreparationInput.model_validate(value, strict=True)
        except (ValidationError, ValueError, TypeError) as error:
            raise MentorAttachmentInvalidError from error

    def _execution_for_step(self, step_input: StepInput) -> _Execution:
        execution = self._execution.get()
        if execution is None:
            request = self._parse_input(step_input.input)
            execution = _Execution(
                request=request,
                owner=request.event_id or request.attachment_id,
            )
            self._execution.set(execution)
        return execution

    def _prepare(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        try:
            execution.prepared = self._prepare_use_case.execute(
                execution.request.attachment_id,
                execution.request.generation,
                execution.owner,
            )
        except Exception:
            try:
                self._release_claim_use_case.execute(
                    execution.request.attachment_id,
                    execution.request.generation,
                    execution.owner,
                )
            finally:
                execution.completed = True
                self._execution.set(None)
            raise
        return StepOutput(
            content=(
                'claimed'
                if execution.prepared is not None
                else 'stale_or_already_claimed'
            )
        )

    def _extract(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        if execution.prepared is None and not execution.completed:
            execution.prepared = self._prepare_use_case.execute(
                execution.request.attachment_id,
                execution.request.generation,
                execution.owner,
            )
        prepared = execution.prepared
        if prepared is None:
            execution.completed = True
            self._execution.set(None)
            return StepOutput(content='no_op')
        heartbeat = _ClaimHeartbeat(
            self._renew_claim_use_case,
            prepared.attachment_id,
            prepared.generation,
            prepared.execution_owner,
        )
        heartbeat.__enter__()
        try:
            extraction = self._extractor_provider.extract(
                prepared.content,
                prepared.media_type,
                prepared.attachment_id,
                prepared.generation,
            )
            if heartbeat.lost:
                execution.prepared = None
                execution.completed = True
                self._execution.set(None)
                return StepOutput(content='stale_claim')

            if prepared.media_type == 'application/pdf':
                visual_pages = tuple(
                    page
                    for page in extraction.uninterpreted_pages
                    if page <= self._max_pdf_pages
                )
            elif prepared.media_type.startswith('image/'):
                visual_pages = (1,)
            else:
                visual_pages = ()

            rendered = self._extractor_provider.render_visual_pages(
                prepared.content, prepared.media_type, visual_pages
            )
            analyzed = set(extraction.analyzed_pages)
            illegible = set(extraction.illegible_pages)
            uninterpreted = set(extraction.uninterpreted_pages)
            chunks = list(extraction.chunks)
            for page_number, image in rendered:
                image_media_type = (
                    prepared.media_type
                    if prepared.media_type.startswith('image/')
                    else 'image/png'
                )
                usage_prefix = f'vision:{prepared.attachment_id}:{page_number}'
                with (
                    inference_guard_scope(
                        lambda: self._assert_claim_current(execution)
                    ),
                    inference_usage_scope(usage_prefix, self._usage_recorder),
                ):
                    output = self._vision_agent.analyze(
                        image,
                        media_type=image_media_type,
                        attachment_id=prepared.attachment_id,
                        page_number=page_number,
                        usage_recorder=self._usage_recorder,
                    )
                uninterpreted.discard(page_number)
                if output.legible:
                    analyzed.add(page_number)
                    illegible.discard(page_number)
                    chunks.append(
                        MentorAttachmentChunk(
                            chunk_id=self._identifier_provider.generate(),
                            attachment_id=prepared.attachment_id,
                            generation=prepared.generation,
                            page_number=page_number,
                            locator=f'page:{page_number}/vision',
                            content=output.description,
                        )
                    )
                else:
                    illegible.add(page_number)
            execution.extraction = MentorAttachmentExtraction(
                chunks=tuple(chunks),
                analyzed_pages=tuple(sorted(analyzed)),
                illegible_pages=tuple(sorted(illegible)),
                uninterpreted_pages=tuple(sorted(uninterpreted)),
                limitations=extraction.limitations,
            )
            return StepOutput(
                content=json.dumps(
                    {
                        'attachment_id': prepared.attachment_id,
                        'chunk_count': len(chunks),
                        'analyzed_page_count': len(analyzed),
                    },
                    separators=(',', ':'),
                )
            )
        except MentorAttachmentInvalidError:
            self._fail_use_case.execute(
                prepared.attachment_id,
                prepared.generation,
                prepared.execution_owner,
                'invalid_file',
            )
            execution.prepared = None
            execution.completed = True
            self._execution.set(None)
            return StepOutput(content='failed_invalid_file')
        except Exception:
            try:
                self._release_claim_use_case.execute(
                    prepared.attachment_id,
                    prepared.generation,
                    prepared.execution_owner,
                )
            finally:
                execution.prepared = None
                execution.completed = True
                self._execution.set(None)
            raise
        finally:
            heartbeat.__exit__()

    def _assert_claim_current(self, execution: _Execution) -> None:
        if not self._renew_claim_use_case.execute(
            execution.request.attachment_id,
            execution.request.generation,
            execution.owner,
        ):
            raise MentorAttachmentUnavailableError

    def _complete(self, step_input: StepInput) -> StepOutput:
        execution = self._execution_for_step(step_input)
        if execution.completed:
            return StepOutput(content='no_op')
        if execution.prepared is None:
            execution.prepared = self._prepare_use_case.execute(
                execution.request.attachment_id,
                execution.request.generation,
                execution.owner,
            )
            if execution.prepared is None:
                execution.completed = True
                self._execution.set(None)
                return StepOutput(content='no_op')
        if execution.extraction is None:
            extraction_output = self._extract(step_input)
            if execution.extraction is None:
                return extraction_output
        prepared = execution.prepared
        extraction = execution.extraction
        try:
            status = self._complete_use_case.execute(
                prepared.attachment_id,
                prepared.generation,
                prepared.execution_owner,
                extraction,
            )
        except Exception:
            try:
                self._release_claim_use_case.execute(
                    prepared.attachment_id,
                    prepared.generation,
                    prepared.execution_owner,
                )
            finally:
                execution.prepared = None
                execution.completed = True
                self._execution.set(None)
            raise
        execution.prepared = None
        execution.completed = True
        self._execution.set(None)
        return StepOutput(
            content=json.dumps(
                {'attachment_id': prepared.attachment_id, 'status': status.value},
                separators=(',', ':'),
            )
        )
