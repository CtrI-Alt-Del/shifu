from shifu.intelligence.core.domain.structures.mentor_summary_boundary import (
    MentorSummaryBoundary,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorMessageVolume:
    count: int
    characters: int
    last_message: (
        MentorSummaryBoundary | None
    )  # newest message outside the recent window
