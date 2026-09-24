from shifu.learning.core.domain.structures.choice_attempt_detail import (
    ChoiceAttemptDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class ChoiceSubmissionOutcome:
    attempt: ChoiceAttemptDetail
    replayed: bool
    is_diagnostic: bool = False
