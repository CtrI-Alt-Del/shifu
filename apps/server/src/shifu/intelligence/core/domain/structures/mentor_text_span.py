from shifu.shared.core.domain.structures import structure


@structure
class MentorTextSpan:
    start: int  # code-point offset, inclusive
    end: int  # code-point offset, exclusive
