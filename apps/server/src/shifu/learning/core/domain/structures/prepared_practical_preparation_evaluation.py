from shifu.shared.core.domain.structures import (
    CurriculumPracticalPreparationQuestionSnapshot,
    structure,
)


@structure
class PreparedPracticePhoto:
    """Reference to a stored photo; the bytes are read later, inside the workflow step."""

    record_key: str
    object_key: str
    media_type: str


@structure
class PreparedPracticalPreparationEvaluation:
    attempt_id: str
    run_id: str
    question: CurriculumPracticalPreparationQuestionSnapshot
    photos: tuple[PreparedPracticePhoto, ...]
