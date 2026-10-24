from typing import ClassVar

from shifu.shared.core.domain.structures import structure


@structure
class LearnerMemoryConcept:
    MAX_CODE_POINTS: ClassVar[int] = 80

    key: str  # normalized lemma form
    label: str  # surface text

    def __post_init__(self) -> None:
        if (
            not self.key
            or not self.label
            or len(self.key) > self.MAX_CODE_POINTS
            or len(self.label) > self.MAX_CODE_POINTS
        ):
            raise ValueError('Invalid learner memory concept')
