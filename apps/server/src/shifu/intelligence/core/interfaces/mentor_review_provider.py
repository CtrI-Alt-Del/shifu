from typing import Protocol
from shifu.intelligence.core.domain.structures import (
    MentorGenerationRequest,
    MentorResponseBlock,
    MentorReviewResult,
)


class MentorReviewProvider(Protocol):
    def review(
        self, request: MentorGenerationRequest, candidate: MentorResponseBlock
    ) -> MentorReviewResult: ...
