from shifu.shared.core.domain.structures import structure


@structure
class PracticalPreparationAnswer:
    """Stored answer: the draft revision confirmed and the reflection frozen at submit."""

    question_key: str
    draft_revision: int
    reflection: str
