from typing import Protocol

from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
)


class CodeRubricAssessorProvider(Protocol):
    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions: ...
