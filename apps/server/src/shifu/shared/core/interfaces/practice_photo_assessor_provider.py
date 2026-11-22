from typing import Protocol

from shifu.shared.core.domain.structures import (
    PracticePhotoAssessmentInput,
    PracticePhotoDecisions,
)


class PracticePhotoAssessorProvider(Protocol):
    def assess(
        self, request: PracticePhotoAssessmentInput
    ) -> PracticePhotoDecisions: ...
