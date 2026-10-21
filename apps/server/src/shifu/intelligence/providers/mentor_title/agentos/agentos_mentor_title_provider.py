from shifu.intelligence.core.domain.errors import (
    MentorTitleOutputInvalidError,
    MentorTitleUnavailableError,
)
from shifu.shared.messaging.agentos.agentos_client import (
    AgentOSClient,
    AgentOSClientError,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import (
    AgentOSHandoffStore,
)

_HANDOFF_CAPABILITY = 'mentor-title-generation'
_WORKFLOW_ID = 'intelligence-generate-mentor-title'


class AgentOSMentorTitleProvider:
    def __init__(
        self,
        client: AgentOSClient,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        self._client = client
        self._handoffs = handoffs

    def generate(self, first_message: str) -> str:
        reference = self._handoffs.create(
            capability=_HANDOFF_CAPABILITY,
            input_value=first_message,
        )
        try:
            self._client.submit_workflow(
                workflow_id=_WORKFLOW_ID,
                fields={'handoff_ref': reference},
                background=False,
                session_id=f'title-{reference}',
                timeout_seconds=3.0,
            )
            result = self._handoffs.take_result(
                reference,
                capability=_HANDOFF_CAPABILITY,
            )
        except AgentOSClientError as error:
            self._handoffs.discard(reference)
            raise MentorTitleUnavailableError from error
        except KeyError as error:
            raise MentorTitleUnavailableError from error

        if not isinstance(result, str):
            raise MentorTitleUnavailableError
        if result == 'invalid':
            raise MentorTitleOutputInvalidError
        if result == 'unavailable':
            raise MentorTitleUnavailableError
        return result
