from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class FillBlanksBlank:
    key: str
    accepted_words: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'key',
            NonEmptyText.create(self.key, error_type=InvalidActivityError).value,
        )
        words = tuple(
            NonEmptyText.create(word, error_type=InvalidActivityError).value
            for word in self.accepted_words
        )
        if not words or len(words) != len(set(words)):
            raise InvalidActivityError

        object.__setattr__(self, 'accepted_words', words)
