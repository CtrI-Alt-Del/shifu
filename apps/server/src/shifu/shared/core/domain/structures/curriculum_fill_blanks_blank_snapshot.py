from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.structures.non_empty_text import NonEmptyText


@structure
class CurriculumFillBlanksBlankSnapshot:
    key: str
    accepted_words: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, 'key', NonEmptyText.create(self.key, error_type=ValidationError).value
        )
        words = tuple(
            NonEmptyText.create(word, error_type=ValidationError).value
            for word in self.accepted_words
        )
        if not words or len(words) != len(set(words)):
            raise ValidationError

        object.__setattr__(self, 'accepted_words', words)
