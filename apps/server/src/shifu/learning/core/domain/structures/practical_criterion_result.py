from shifu.shared.core.domain.structures import structure


@structure
class PracticalCriterionResult:
    """One validated criterion observation; a null level means inconclusive."""

    criterion_key: str
    level: int | None
    comment_key: str | None
