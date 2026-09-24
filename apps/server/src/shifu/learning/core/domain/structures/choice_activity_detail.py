from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures.choice_question_detail import (
    ChoiceQuestionDetail,
)
from shifu.shared.core.domain.structures import structure


@structure
class ChoiceActivityDetail:
    activity_id: str
    title: str
    difficulty: ActivityDifficulty
    questions: tuple[ChoiceQuestionDetail, ...]
    can_submit: bool
    latest_attempt_id: str | None = None
    unresolved_attempt_id: str | None = None
    is_diagnostic: bool = False
