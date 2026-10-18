import json
from contextvars import ContextVar
from typing import cast

from agno.run.workflow import WorkflowRunOutput
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.use_cases import PurgeMentorAttachmentsUseCase


class _PurgeInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    account_id: str = Field(pattern=r'^[0-9A-HJKMNP-TV-Z]{26}$')
    session_id: str | None = Field(default=None, pattern=r'^[0-9A-HJKMNP-TV-Z]{26}$')
    batch_id: str | None = Field(default=None, pattern=r'^[0-9A-HJKMNP-TV-Z]{26}$')
    deletion_generation: int = Field(ge=1)


class PurgeMentorAttachmentsWorkflow(Workflow):
    def __init__(self, purge_use_case: PurgeMentorAttachmentsUseCase) -> None:
        super().__init__(
            id='intelligence-purge-mentor-attachments',
            name='purge-mentor-attachments',
            steps=[
                Step(
                    name='purge-private-artifacts', executor=self._purge, max_retries=0
                )
            ],
            telemetry=False,
            store_events=False,
            store_executor_outputs=False,
        )
        self._purge_use_case = purge_use_case
        self._request: ContextVar[_PurgeInput | None] = ContextVar(
            'purge_mentor_attachments_request', default=None
        )

    def deep_copy(
        self, *, update: dict[str, object] | None = None
    ) -> 'PurgeMentorAttachmentsWorkflow':
        workflow = PurgeMentorAttachmentsWorkflow(self._purge_use_case)
        workflow.db = self.db
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    def run(  # pyright: ignore[reportIncompatibleMethodOverride] - This boundary accepts only a normalized event payload.
        self, input: object
    ) -> WorkflowRunOutput:
        request = self._parse_input(input)
        token = self._request.set(request)
        try:
            return super().run(input=request.model_dump_json())
        finally:
            self._request.reset(token)

    @staticmethod
    def _parse_input(raw: object) -> _PurgeInput:
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(raw, str) and isinstance(value, dict):
                payload = cast('dict[str, object]', value)
                generation = payload.get('deletion_generation')
                if isinstance(generation, str) and generation.isdecimal():
                    value = {**payload, 'deletion_generation': int(generation)}
            request = _PurgeInput.model_validate(value, strict=True)
        except (ValidationError, ValueError, TypeError) as error:
            raise MentorAttachmentInvalidError from error
        if (request.session_id is None) == (request.batch_id is None):
            raise MentorAttachmentInvalidError
        return request

    def _purge(self, _step_input: StepInput) -> StepOutput:
        request = self._request.get()
        if request is None:
            request = self._parse_input(_step_input.input)
        removed = self._purge_use_case.execute(
            request.account_id,
            request.session_id,
            request.batch_id,
            request.deletion_generation,
        )
        return StepOutput(content=json.dumps({'removed_objects': removed}))
