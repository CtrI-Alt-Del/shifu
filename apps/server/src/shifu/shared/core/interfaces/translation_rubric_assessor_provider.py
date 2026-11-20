from typing import Protocol

from shifu.shared.core.domain.structures import (
    CodeRubricDecisions,
    TranslationRubricAssessmentInput,
)


class TranslationRubricAssessorProvider(Protocol):
    def assess(
        self, request: TranslationRubricAssessmentInput
    ) -> CodeRubricDecisions: ...
