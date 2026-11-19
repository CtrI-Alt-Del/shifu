from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures.choice_question_detail import (
    ChoiceQuestionDetail,
)
from shifu.shared.core.domain.structures import structure
from shifu.learning.core.domain.structures.code_question_detail import (
    CodeQuestionDetail,
)
from shifu.learning.core.domain.structures.ordering_question_detail import (
    OrderingQuestionDetail,
)


@structure
class ChoiceActivityDetail:
    activity_id: str
    title: str
    difficulty: ActivityDifficulty
    questions: tuple[
        ChoiceQuestionDetail | CodeQuestionDetail | OrderingQuestionDetail, ...
    ]
    can_submit: bool
    latest_attempt_id: str | None = None
    unresolved_attempt_id: str | None = None
    is_diagnostic: bool = False
    activity_revision: str | None = None
    ordering_passage_key: str | None = None
