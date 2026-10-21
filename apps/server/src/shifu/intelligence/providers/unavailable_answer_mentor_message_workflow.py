from collections.abc import Callable

from shifu.intelligence.core.domain.enums import MentorWorkflowStep
from shifu.intelligence.core.domain.structures import (
    MentorGenerationRequest,
    MentorResponseBlock,
    MentorInferenceUsage,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


class UnavailableAnswerMentorMessageWorkflow:
    """No commercial inference until the approved model and privacy route exist."""

    def run(
        self,
        request: MentorGenerationRequest,
        usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
        inference_guard: Callable[[], None] | None = None,
        progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
    ) -> MentorResponseBlock:
        raise ServiceUnavailableError('A geração do Mentor está indisponível.')
