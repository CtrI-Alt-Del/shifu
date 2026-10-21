import json

from agno.exceptions import OutputCheckError, SchemaMismatchError
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow
from pydantic import ValidationError as PydanticValidationError

from shifu.intelligence.ai.generative.agno.agents.mentor_title_agent import (
    MentorTitleAgent,
)
from shifu.intelligence.ai.generative.agno.outputs.mentor_title_output import (
    MentorTitleOutput,
)
from shifu.intelligence.core.domain.errors import (
    MentorTitleOutputInvalidError,
    MentorTitleUnavailableError,
)


class AgnoGenerateMentorTitleWorkflow(Workflow):
    def __init__(self, agent: MentorTitleAgent) -> None:
        super().__init__(
            name='generate-mentor-title',
            steps=[Step(name='generate-title', agent=agent)],
            telemetry=False,
            store_events=False,
            store_executor_outputs=False,
        )

    def generate(self, first_message: str) -> str:
        try:
            response = super().run(input=first_message)
        except (
            PydanticValidationError,
            OutputCheckError,
            SchemaMismatchError,
        ) as error:
            raise MentorTitleOutputInvalidError from error
        except Exception as error:
            raise MentorTitleUnavailableError from error

        if not response.has_completed():
            raise MentorTitleUnavailableError

        content = response.content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as error:
                raise MentorTitleUnavailableError from error

        try:
            output = MentorTitleOutput.model_validate(content)
        except (PydanticValidationError, AttributeError, TypeError) as error:
            raise MentorTitleOutputInvalidError from error
        return output.title
