from shifu.shared.core.domain.structures import structure


@structure
class PracticalPreparationAnswerSubmission:
    """What the client sends: the draft revision it saw. Photos and reflection live in the draft."""

    question_key: str
    draft_revision: int
