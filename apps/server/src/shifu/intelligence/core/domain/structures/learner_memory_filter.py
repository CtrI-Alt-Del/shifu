from typing import ClassVar

from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)
from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryFilter:
    MAX_QUERY_CODE_POINTS: ClassVar[int] = 100

    query: str | None = None  # trimmed
    category: LearnerMemoryCategory | None = None

    def __post_init__(self) -> None:
        if self.query is not None and (
            self.query != self.query.strip()
            or len(self.query) > self.MAX_QUERY_CODE_POINTS
        ):
            raise ValueError('Invalid learner memory filter')
