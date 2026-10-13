"""Application-owned native Mentor workflow and commercial transport lifecycle."""

from shifu.intelligence.core.interfaces import AnswerMentorMessageWorkflow
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.intelligence.providers.unavailable_answer_mentor_message_workflow import (
    UnavailableAnswerMentorMessageWorkflow,
)
from shifu.shared.settings import Settings


class MentorAnswerRuntime:
    workflow: AnswerMentorMessageWorkflow

    def __init__(
        self,
        workflow: AnswerMentorMessageWorkflow,
    ) -> None:
        self.workflow = workflow

    @classmethod
    def build(
        cls, settings: Settings, telemetry: LangfuseMentorTelemetryProvider
    ) -> 'MentorAnswerRuntime':
        del settings, telemetry
        return cls(UnavailableAnswerMentorMessageWorkflow())

    def close(self) -> None:
        return
