from shifu.shared.core.domain.structures import structure


@structure
class MentorReviewResult:
    approved: bool
    criteria: tuple[tuple[str, str, float | None], ...]
    correction: str | None
    probabilities: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] = ()
    feedback: tuple[tuple[str, str], ...] = ()
