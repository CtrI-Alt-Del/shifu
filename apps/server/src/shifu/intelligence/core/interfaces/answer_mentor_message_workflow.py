from collections.abc import Callable
from typing import Protocol
from shifu.intelligence.core.domain.enums import MentorWorkflowStep
from shifu.intelligence.core.domain.structures import (
    MentorGenerationRequest,
    MentorInferenceUsage,
    MentorResponseBlock,
)


class AnswerMentorMessageWorkflow(Protocol):
    def run(
        self,
        request: MentorGenerationRequest,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
        inference_guard: Callable[[], None] | None = None,
        progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
    ) -> MentorResponseBlock: ...
