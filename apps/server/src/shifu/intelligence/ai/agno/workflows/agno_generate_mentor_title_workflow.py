from __future__ import annotations

import json
from time import perf_counter
from typing import TYPE_CHECKING, Literal, cast
from uuid import uuid4

from agno.exceptions import OutputCheckError, SchemaMismatchError
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import ValidationError as PydanticValidationError

from shifu.intelligence.ai.agno.outputs import MentorTitleOutput
from shifu.shared.messaging.agentos.workflow_helpers import copy_agent

if TYPE_CHECKING:
    from collections.abc import Callable

    from shifu.intelligence.ai.agno.agents import MentorTitleAgent
    from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore

    from shifu.shared.providers.langfuse_telemetry_provider import (
        LangfuseTelemetryProvider,
    )


_HANDOFF_CAPABILITY = 'mentor-title-generation'


class AgnoGenerateMentorTitleWorkflow(Workflow):
    def __init__(
        self,
        agent: MentorTitleAgent,
        handoffs: AgentOSHandoffStore,
        observability: LangfuseTelemetryProvider | None = None,
    ) -> None:
        self._observability: LangfuseTelemetryProvider | None = observability
        self._handoffs = handoffs
        self._agent = agent
        super().__init__(
            id='intelligence-generate-mentor-title',
            name='Generate Mentor Title',
            steps=[
                Step(
                    name='generate-title',
                    executor=cast('Callable[[StepInput], StepOutput]', self._generate),
                    max_retries=0,
                )
            ],
            telemetry=False,
            store_events=False,
            store_media=False,
            store_executor_outputs=False,
            cache_session=False,
        )

    def deep_copy(
        self, *, update: dict[str, object] | None = None
    ) -> AgnoGenerateMentorTitleWorkflow:
        workflow = AgnoGenerateMentorTitleWorkflow(
            copy_agent(self._agent), self._handoffs, self._observability
        )
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    def _generate(self, step_input: StepInput) -> StepOutput:
        started = perf_counter()
        outcome: Literal['passed', 'failed'] = 'failed'
        try:
            result = self._generate_title(step_input)
            if result.content == {'status': 'complete'}:
                outcome = 'passed'
            return result
        finally:
            if self._observability is not None:
                self._observability.record(
                    stage='title',
                    outcome=outcome,
                    duration_ms=(perf_counter() - started) * 1000,
                    correlation_id=uuid4().hex,
                    model_profile='openrouter-title',
                )

    def _generate_title(self, step_input: StepInput) -> StepOutput:
        reference = self._reference(step_input.input)
        if reference is None:
            return StepOutput(content={'status': 'invalid_request'})
        try:
            first_message = self._handoffs.read_input(
                reference,
                capability=_HANDOFF_CAPABILITY,
            )
            if not isinstance(first_message, str):
                self._handoffs.complete(
                    reference,
                    capability=_HANDOFF_CAPABILITY,
                    result_value='invalid',
                )
                return StepOutput(content={'status': 'invalid_request'})
            response = self._agent.run(first_message)  # pyright: ignore[reportUnknownMemberType] - Agno Agent lacks complete stubs.
            content = response.content
            if isinstance(content, str):
                content = json.loads(content)
            output = MentorTitleOutput.model_validate(content)
        except (
            json.JSONDecodeError,
            PydanticValidationError,
            OutputCheckError,
            SchemaMismatchError,
        ):
            self._complete(reference, 'invalid')
            return StepOutput(content={'status': 'invalid_output'})
        except Exception:  # noqa: BLE001 - keep model errors out of AgentOS state.
            self._complete(reference, 'unavailable')
            return StepOutput(content={'status': 'unavailable'})

        self._complete(reference, output.title)
        return StepOutput(content={'status': 'complete'})

    def _complete(self, reference: str, result_value: str) -> None:
        try:
            self._handoffs.complete(
                reference,
                capability=_HANDOFF_CAPABILITY,
                result_value=result_value,
            )
        except KeyError:
            return

    @staticmethod
    def _reference(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        try:
            envelope = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(envelope, dict):
            return None
        payload = cast('dict[str, object]', envelope)
        reference = payload.get('handoff_ref')
        if set(payload) != {'handoff_ref'} or not isinstance(reference, str):
            return None
        return reference
