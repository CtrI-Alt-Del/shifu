from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText
from shifu.shared.core.domain.structures.structure import structure


@structure
class CurriculumPairMatchingItemSnapshot:
    key: str
    text: str

    def __post_init__(self) -> None:
        NonEmptyText.create(self.key, error_type=ValidationError)
        NonEmptyText.create(self.text, error_type=ValidationError)
