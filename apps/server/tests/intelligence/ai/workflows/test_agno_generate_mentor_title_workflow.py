"""The title workflow run in process with a mocked title agent. The handoff store
is real: the workflow reads the first message from it and writes the title back."""

from __future__ import annotations

import json
from unittest.mock import Mock

from agno.run.agent import RunOutput
from agno.run.base import RunStatus
import pytest

from shifu.intelligence.ai.agno.agents import MentorTitleAgent
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
