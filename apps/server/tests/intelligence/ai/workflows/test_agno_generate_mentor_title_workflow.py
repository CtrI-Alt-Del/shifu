"""The title workflow run in process with a mocked title agent. The handoff store
is real: the workflow reads the first message from it and writes the title back."""

from __future__ import annotations

import json
from unittest.mock import Mock

from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat
from agno.models.response import ModelResponse
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
import pytest

from shifu.intelligence.ai.agno.agents import MentorTitleAgent
from shifu.intelligence.ai.agno.agents.mentor_agent import (
    _MentorOpenAIChat,  # pyright: ignore[reportPrivateUsage] - the test drives the real Mentor model class.
)
from shifu.intelligence.ai.agno.outputs import MentorTitleOutput
from shifu.intelligence.ai.agno.workflows import AgnoGenerateMentorTitleWorkflow
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore

CAPABILITY = 'mentor-title-generation'
FIRST_MESSAGE = 'Estou estudando frações equivalentes. Explique com um exemplo visual.'


@pytest.fixture
def agent() -> Mock:
    agent = Mock(spec=MentorTitleAgent)
    agent.run.return_value = RunOutput(
        content=MentorTitleOutput(title='Frações equivalentes'),
        status=RunStatus.completed,
    )
    return agent


@pytest.fixture
def handoffs() -> AgentOSHandoffStore:
    return AgentOSHandoffStore()


@pytest.fixture
def workflow(
    agent: Mock, handoffs: AgentOSHandoffStore
) -> AgnoGenerateMentorTitleWorkflow:
    return AgnoGenerateMentorTitleWorkflow(agent, handoffs)


def submit(workflow: AgnoGenerateMentorTitleWorkflow, reference: str) -> object:
    return workflow.run(input=json.dumps({'handoff_ref': reference})).content


class TestAgnoGenerateMentorTitleWorkflow:
    def test_writes_the_generated_title_to_the_handoff(
        self,
        workflow: AgnoGenerateMentorTitleWorkflow,
        agent: Mock,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        assert submit(workflow, reference) == {'status': 'complete'}

        agent.run.assert_called_once_with(FIRST_MESSAGE)
        assert handoffs.take_result(reference, capability=CAPABILITY) == (
            'Frações equivalentes'
        )

    def test_marks_an_output_without_a_title_invalid(
        self,
        workflow: AgnoGenerateMentorTitleWorkflow,
        agent: Mock,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        agent.run.return_value = RunOutput(
            content={'headline': 'sem título'}, status=RunStatus.completed
        )
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        assert submit(workflow, reference) == {'status': 'invalid_output'}

        assert handoffs.take_result(reference, capability=CAPABILITY) == 'invalid'

    def test_marks_the_title_unavailable_when_the_agent_raises(
        self,
        workflow: AgnoGenerateMentorTitleWorkflow,
        agent: Mock,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        agent.run.side_effect = RuntimeError('model endpoint down')
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        assert submit(workflow, reference) == {'status': 'unavailable'}

        assert handoffs.take_result(reference, capability=CAPABILITY) == 'unavailable'

    def test_rejects_a_malformed_envelope_without_calling_the_agent(
        self,
        workflow: AgnoGenerateMentorTitleWorkflow,
        agent: Mock,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        output = workflow.run(
            input=json.dumps({'handoff_ref': reference, 'extra': 'field'})
        ).content

        assert output == {'status': 'invalid_request'}
        agent.run.assert_not_called()
        # The handoff is untouched: its input is still readable.
        assert handoffs.read_input(reference, capability=CAPABILITY) == FIRST_MESSAGE

    def test_marks_a_non_text_handoff_input_invalid(
        self,
        workflow: AgnoGenerateMentorTitleWorkflow,
        agent: Mock,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        reference = handoffs.create(capability=CAPABILITY, input_value=42)

        assert submit(workflow, reference) == {'status': 'invalid_request'}

        agent.run.assert_not_called()
        assert handoffs.take_result(reference, capability=CAPABILITY) == 'invalid'


class TestAgnoGenerateMentorTitleWorkflowWithTheMentorModel:
    """The real title agent and Mentor model; only the provider call is replaced.

    The Mentor model reads its transport failure from a scope the workflow must
    open. A mocked agent cannot show a run that leaves the scope out."""

    @staticmethod
    def real_agent(monkeypatch: pytest.MonkeyPatch) -> MentorTitleAgent:
        def respond(*_args: object, **_kwargs: object) -> ModelResponse:
            return ModelResponse(
                role='assistant',
                content=MentorTitleOutput(
                    title='Frações equivalentes'
                ).model_dump_json(),
            )

        monkeypatch.setattr(OpenAIChat, 'invoke', respond)
        agent = MentorTitleAgent()
        agent.model = _MentorOpenAIChat(id='openai/test-model', api_key='test-key')
        return agent

    def test_generates_a_title_through_the_mentor_model(
        self, monkeypatch: pytest.MonkeyPatch, handoffs: AgentOSHandoffStore
    ) -> None:
        workflow = AgnoGenerateMentorTitleWorkflow(
            self.real_agent(monkeypatch), handoffs
        )
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        assert submit(workflow, reference) == {'status': 'complete'}

        assert handoffs.take_result(reference, capability=CAPABILITY) == (
            'Frações equivalentes'
        )

    def test_marks_the_title_unavailable_when_the_provider_fails(
        self, monkeypatch: pytest.MonkeyPatch, handoffs: AgentOSHandoffStore
    ) -> None:
        def fail(*_args: object, **_kwargs: object) -> ModelResponse:
            raise ModelProviderError('provider down', status_code=503)

        agent = self.real_agent(monkeypatch)
        monkeypatch.setattr(OpenAIChat, 'invoke', fail)
        workflow = AgnoGenerateMentorTitleWorkflow(agent, handoffs)
        reference = handoffs.create(capability=CAPABILITY, input_value=FIRST_MESSAGE)

        assert submit(workflow, reference) == {'status': 'unavailable'}

        assert handoffs.take_result(reference, capability=CAPABILITY) == 'unavailable'
